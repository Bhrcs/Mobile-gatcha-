#pragma once
// Shared helpers for the data-driven game logic. Everything the Godot version
// kept in Dictionaries is a Json value here (ordered, so iteration order matches
// the data files). Accessors never throw: a missing key or wrong type gives the
// fallback, exactly like Dictionary.get(key, default).
#include "json.hpp"
#include <algorithm>
#include <functional>
#include <random>
#include <string>
#include <vector>

using Json = nlohmann::ordered_json;

inline const Json& at(const Json& j, const std::string& k)
{
    static const Json null;
    if (j.is_object())
    {
        auto it = j.find(k);
        if (it != j.end())
            return *it;
    }
    return null;
}
inline const Json& at(const Json& j, size_t i)
{
    static const Json null;
    return j.is_array() && i < j.size() ? j[i] : null;
}
inline int I(const Json& j, int d = 0)
{
    if (j.is_number_integer()) return (int)j.get<int64_t>();
    if (j.is_number()) return (int)j.get<double>();
    if (j.is_boolean()) return j.get<bool>() ? 1 : 0;
    return d;
}
inline double F(const Json& j, double d = 0.0) { return j.is_number() ? j.get<double>() : d; }
inline std::string S(const Json& j) { return j.is_string() ? j.get<std::string>() : std::string(); }
inline bool B(const Json& j, bool d = false)
{
    if (j.is_boolean()) return j.get<bool>();
    if (j.is_number()) return j.get<double>() != 0.0;
    return d;
}
// shorthand: I(d, "key", 1) == int(d.get("key", 1))
inline int I(const Json& j, const std::string& k, int d) { return I(at(j, k), d); }
inline double F(const Json& j, const std::string& k, double d) { return F(at(j, k), d); }
inline std::string S(const Json& j, const std::string& k, const std::string& d = "")
{
    const Json& v = at(j, k);
    return v.is_string() ? v.get<std::string>() : d;
}
inline bool B(const Json& j, const std::string& k, bool d) { return B(at(j, k), d); }
inline const Json& A(const Json& j, const std::string& k)  // array or empty array
{
    static const Json empty = Json::array();
    const Json& v = at(j, k);
    return v.is_array() ? v : empty;
}
inline const Json& O(const Json& j, const std::string& k)  // object or empty object
{
    static const Json empty = Json::object();
    const Json& v = at(j, k);
    return v.is_object() ? v : empty;
}
inline bool contains(const Json& arr, const Json& v)
{
    return arr.is_array() && std::find(arr.begin(), arr.end(), v) != arr.end();
}
inline void erase_value(Json& arr, const Json& v)
{
    if (!arr.is_array()) return;
    for (auto it = arr.begin(); it != arr.end(); ++it)
        if (*it == v) { arr.erase(it); return; }
}
inline std::string capitalize(std::string s)
{
    for (auto& c : s) if (c == '_') c = ' ';
    bool up = true;
    for (auto& c : s) { c = up ? (char)toupper(c) : c; up = c == ' '; }
    return s;
}
inline std::string upper(std::string s) { for (auto& c : s) c = (char)toupper(c); return s; }
std::string fmt_number(long long n);   // 1,234,567 (Progression.cpp)

// Minimal signal: connect() returns an id for disconnect(). Handlers may disconnect
// themselves while the signal is emitting.
template <typename... Args>
class Signal
{
public:
    int connect(std::function<void(Args...)> f) { _slots.push_back({++_next, std::move(f)}); return _next; }
    void disconnect(int id)
    {
        for (auto& s : _slots) if (s.first == id) s.second = nullptr;
    }
    void emit(Args... a)
    {
        auto copy = _slots;
        for (auto& s : copy) if (s.second) s.second(a...);
        _slots.erase(std::remove_if(_slots.begin(), _slots.end(), [](auto& s) { return !s.second; }), _slots.end());
    }
    void clear() { _slots.clear(); }
private:
    std::vector<std::pair<int, std::function<void(Args...)>>> _slots;
    int _next = 0;
};

// Godot's RandomNumberGenerator interface over mt19937.
struct Rng
{
    std::mt19937 gen{std::random_device{}()};
    void seed(unsigned s) { gen.seed(s); }
    void randomize() { gen.seed(std::random_device{}()); }
    double randf() { return std::uniform_real_distribution<double>(0.0, 1.0)(gen); }
    double randf_range(double a, double b) { return a + (b - a) * randf(); }
    int randi_range(int a, int b) { return a >= b ? a : std::uniform_int_distribution<int>(a, b)(gen); }
};
