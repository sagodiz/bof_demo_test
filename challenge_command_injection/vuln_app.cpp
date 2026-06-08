#include <iostream>
#include <fstream>
#include <cstring>
#include <libpq-fe.h>
#include <opencv2/opencv.hpp>

struct User {
    char name[10];    // intentionally small for overflow demo
    bool freetier;
};

// Simple helper to read user from PostgreSQL
bool load_user(const std::string& username, User& user) {
    const char* conninfo = "host=localhost dbname=bofdb user=bofuser password=bofpass";
    PGconn* conn = PQconnectdb(conninfo);

    if (PQstatus(conn) != CONNECTION_OK) {
        std::cerr << "DB connection failed\n";
        PQfinish(conn);
        return false;
    }

    std::string query = "SELECT name, freetier FROM users WHERE name = '" + username + "';";
    PGresult* res = PQexec(conn, query.c_str());

    if (PQresultStatus(res) != PGRES_TUPLES_OK || PQntuples(res) != 1) {
        std::cerr << "User not found\n";
        PQclear(res);
        PQfinish(conn);
        return false;
    }

    const char* db_name = PQgetvalue(res, 0, 0);
    const char* db_freetier = PQgetvalue(res, 0, 1);

    // Vulnerable strcpy -> overflow possible. Order matters

    strncpy(user.name, db_name, sizeof(user.name));
    user.freetier = (db_freetier[0] == 't');

    PQclear(res);
    PQfinish(conn);
    return true;
}

// Simple image processing: rotate 90 deg and add watermark if free tier
bool process_image(const std::string& input_file, const std::string& output_file, const User& user) {
    cv::Mat img = cv::imread(input_file);
    if (img.empty()) {
        std::cerr << "Cannot read input image\n";
        return false;
    }

    // Rotate 90 degrees clockwise
    cv::rotate(img, img, cv::ROTATE_90_CLOCKWISE);

    // Add watermark if free tier
    std::string text;
    if (user.freetier) {
        text = "FREE - TRY AGAIN";
    } else {
        text = "DACHSHUND";
    }
    int font = cv::FONT_HERSHEY_SIMPLEX;
    double scale = 2.0;
    int thickness = 3;
    cv::putText(img, text, cv::Point(10, img.rows - 20), font, scale, cv::Scalar(0, 0, 255), thickness);


    return cv::imwrite(output_file, img);
}

int main(int argc, char* argv[]) {
    if (argc < 4) {
        std::cerr << "Usage: " << argv[0] << "<username> <input_file> <output_file>\n";
        return 1;
    }

    std::string username = argv[1];
    std::string input_file = argv[2];
    std::string output_file = argv[3];

    User user{};
    if (!load_user(username, user)) {
        return 2;
    }

    std::cout << "Loaded user: " << user.name << " freetier=" << user.freetier << "\n";

    if (!process_image(input_file, output_file, user)) {
        return 3;
    }

    std::cout << "Image processed and saved to " << output_file << "\n";
    return 0;
}
