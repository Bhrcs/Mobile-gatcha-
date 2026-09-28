// Platform services for the logic layer, backed by Axmol's FileUtils.
#include "logic/Platform.h"
#include "axmol.h"
#include <chrono>
#include <ctime>

namespace Platform
{
static ax::FileUtils* fu() { return ax::FileUtils::getInstance(); }
static std::string full(const std::string& p)   // absolute paths pass through, content paths resolve
{
    return fu()->isAbsolutePath(p) ? p : fu()->fullPathForFilename(p);
}
std::string readText(const std::string& path)
{
    std::string f = full(path);
    return f.empty() || !fu()->isFileExist(f) ? std::string() : fu()->getStringFromFile(f);
}
bool fileExists(const std::string& path) { std::string f = full(path); return !f.empty() && fu()->isFileExist(f); }
bool writeText(const std::string& path, const std::string& text) { return fu()->writeStringToFile(text, path); }
bool removeFile(const std::string& path) { return fu()->isFileExist(path) && fu()->removeFile(path); }
bool renameFile(const std::string& from, const std::string& to)
{
    if (fu()->isFileExist(to)) fu()->removeFile(to);
    return fu()->renameFile(from, to);
}
std::string writablePath()
{
    std::string p = fu()->getWritablePath();
    if (!p.empty() && p.back() != '/' && p.back() != '\\') p += '/';
    fu()->createDirectories(p);
    return p;
}
double now()
{
    using namespace std::chrono;
    return duration<double>(system_clock::now().time_since_epoch()).count();
}
int tzBiasMinutes()
{
    std::time_t t = std::time(nullptr);
    std::tm lt{}, gt{};
#ifdef _WIN32
    localtime_s(&lt, &t);
    gmtime_s(&gt, &t);
#else
    localtime_r(&t, &lt);
    gmtime_r(&t, &gt);
#endif
    return (int)std::difftime(std::mktime(&lt), std::mktime(&gt)) / 60;
}
void log(const std::string& msg) { AXLOGI("{}", msg); }
}  // namespace Platform
