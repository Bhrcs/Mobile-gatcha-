#pragma once
// The few OS services the logic layer needs. PlatformAx.cpp implements them with
// Axmol's FileUtils (game); Tests/PlatformStd.cpp with the standard library (tests).
#include <string>

namespace Platform
{
std::string readText(const std::string& path);      // "" when missing
bool fileExists(const std::string& path);
bool writeText(const std::string& path, const std::string& text);
bool removeFile(const std::string& path);
bool renameFile(const std::string& from, const std::string& to);
std::string writablePath();                          // ends with '/'
double now();                                        // unix seconds
int tzBiasMinutes();                                 // local time - UTC, minutes
void log(const std::string& msg);
}  // namespace Platform
