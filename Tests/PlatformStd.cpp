// Standard-library Platform for the engine-free logic tests (Tests/run_logic_tests.sh).
#include "logic/Platform.h"
#include <chrono>
#include <cstdio>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>

namespace fs = std::filesystem;
static std::string content_root() { const char* r = std::getenv("CONTENT_ROOT"); return r ? r : "Content/"; }
static std::string full(const std::string& p) { return p.empty() || p[0] == '/' ? p : content_root() + p; }

namespace Platform
{
std::string readText(const std::string& path)
{
    std::ifstream f(full(path), std::ios::binary);
    std::stringstream ss;
    ss << f.rdbuf();
    return ss.str();
}
bool fileExists(const std::string& path) { return fs::exists(full(path)); }
bool writeText(const std::string& path, const std::string& text)
{
    std::ofstream f(path, std::ios::binary);
    f << text;
    return bool(f);
}
bool removeFile(const std::string& path) { std::error_code ec; return fs::remove(path, ec); }
bool renameFile(const std::string& a, const std::string& b) { std::error_code ec; fs::rename(a, b, ec); return !ec; }
std::string writablePath() { auto p = fs::temp_directory_path() / "cinderbound_test/"; fs::create_directories(p); return p.string(); }
double now() { return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count(); }
int tzBiasMinutes() { std::time_t t = std::time(nullptr); std::tm l = *std::localtime(&t), g = *std::gmtime(&t); return int(std::difftime(std::mktime(&l), std::mktime(&g)) / 60); }
void log(const std::string& msg) { std::cerr << msg << "\n"; }
}  // namespace Platform
