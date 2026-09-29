#include "Gui.h"
#include "ui/UIScale9Sprite.h"
#include <chrono>
#include <cmath>
#include <unordered_map>

using namespace ax;

namespace gd
{
static bool g_dirty = true;
static int g_seq = 0;
static std::vector<std::function<void()>> g_deferred;
static Root* g_root = nullptr;

void Root::mark_dirty() { g_dirty = true; }

// ================================================================== Col
const Col Col::WHITE(1, 1, 1, 1), Col::BLACK(0, 0, 0, 1), Col::CLEAR(0, 0, 0, 0);

Col::Col(const char* hex)
{
    std::string h = hex ? hex : "";
    if (!h.empty() && h[0] == '#') h = h.substr(1);
    auto byte = [&](size_t i) { return i + 2 <= h.size() ? std::stoi(h.substr(i, 2), nullptr, 16) / 255.0f : 1.0f; };
    if (h.size() == 6 || h.size() == 8)
    {
        r = byte(0);
        g = byte(2);
        b = byte(4);
        a = h.size() == 8 ? byte(6) : 1.0f;
    }
}
static uint8_t u8(float v) { return (uint8_t)std::lround(std::clamp(v, 0.0f, 1.0f) * 255.0f); }
Color4B Col::c4b() const { return Color4B(u8(r), u8(g), u8(b), u8(a)); }
Color3B Col::c3b() const { return Color3B(u8(r), u8(g), u8(b)); }

// ================================================================== helpers
double ticks()
{
    static auto start = std::chrono::steady_clock::now();
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
}

std::string font_path() { return "assets/fonts/cinder_pixel.ttf"; }

bool exists(const std::string& path) { return !path.empty() && FileUtils::getInstance()->isFileExist(path); }

Texture2D* texture(const std::string& path)
{
    if (path.empty()) return nullptr;
    std::string p = path.rfind("res://", 0) == 0 ? path.substr(6) : path;
    auto tc = Director::getInstance()->getTextureCache();
    Texture2D* t = tc->getTextureForKey(p);
    if (!t)
    {
        if (!FileUtils::getInstance()->isFileExist(p)) return nullptr;
        t = tc->addImage(p);
        if (t) t->setAliasTexParameters();
    }
    return t;
}

Texture2D* white_texture()
{
    static Texture2D* t = nullptr;
    if (!t)
    {
        std::vector<uint8_t> px(4 * 4 * 4, 255);
        t = new Texture2D();
        t->initWithData(px.data(), px.size(), backend::PixelFormat::RGBA8, 4, 4);
        t->setAliasTexParameters();
    }
    return t;
}

Texture2D* gradient_texture(const std::vector<std::pair<float, Col>>& stops, int w, int h, bool radial, Vec2 from, Vec2 to)
{
    std::vector<uint8_t> px(size_t(w) * h * 4);
    auto sample = [&](float t) {
        if (stops.empty()) return Col::WHITE;
        if (t <= stops.front().first) return stops.front().second;
        for (size_t i = 1; i < stops.size(); ++i)
            if (t <= stops[i].first)
            {
                float span = std::max(1e-5f, stops[i].first - stops[i - 1].first);
                return stops[i - 1].second.lerp(stops[i].second, (t - stops[i - 1].first) / span);
            }
        return stops.back().second;
    };
    Vec2 d = to - from;
    float len2 = std::max(1e-6f, d.lengthSquared());
    for (int y = 0; y < h; ++y)
        for (int x = 0; x < w; ++x)
        {
            Vec2 uv((x + 0.5f) / w, (y + 0.5f) / h);   // top-left origin, like Godot
            float t = radial ? (uv - from).length() / std::sqrt(len2) : (uv - from).dot(d) / len2;
            Col c = sample(std::clamp(t, 0.0f, 1.0f));
            uint8_t* p = &px[(size_t(y) * w + x) * 4];
            p[0] = u8(c.r); p[1] = u8(c.g); p[2] = u8(c.b); p[3] = u8(c.a);
        }
    auto t = new Texture2D();
    t->initWithData(px.data(), px.size(), backend::PixelFormat::RGBA8, w, h);
    t->autorelease();
    return t;
}

static TTFConfig ttf(int size, int outline)
{
    TTFConfig c(font_path(), (float)size, GlyphCollection::DYNAMIC, nullptr, false, 0);
    (void)outline;
    return c;
}

static ax::Label* make_label(int size, int outline, const Col& outline_col)
{
    auto l = ax::Label::createWithTTF(ttf(size, outline), "");
    if (!l) l = ax::Label::createWithSystemFont("", "Arial", (float)size);
    if (outline > 0) l->enableOutline(outline_col.c4b(), std::max(1, outline / 2));
    if (auto fa = l->getFontAtlas()) fa->setAliasTexParameters();
    l->setAnchorPoint(Vec2::ZERO);
    return l;
}

ax::Size text_size(const std::string& text, int font_size, float wrap_width, int outline)
{
    static std::unordered_map<std::string, ax::Size> cache;
    static std::map<std::pair<int, int>, ax::Label*> measurers;
    std::string key = std::to_string(font_size) + "|" + std::to_string((int)wrap_width) + "|" + std::to_string(outline) + "|" + text;
    auto it = cache.find(key);
    if (it != cache.end()) return it->second;
    auto& m = measurers[{font_size, outline}];
    if (!m)
    {
        m = make_label(font_size, outline, Col::BLACK);
        m->retain();
        m->setLineSpacing(6);
    }
    m->setDimensions(wrap_width > 0 ? wrap_width : 0, 0);
    m->setString(text.empty() ? " " : text);
    ax::Size s = m->getContentSize();
    if (text.empty()) s.x = 0;
    if (cache.size() > 20000) cache.clear();
    cache[key] = s;
    return s;
}

void after(Node* owner, float seconds, std::function<void()> f)
{
    if (!owner) return;
    owner->runAction(Sequence::create(DelayTime::create(std::max(0.0f, seconds)), CallFunc::create(std::move(f)), nullptr));
}

void defer(std::function<void()> f) { g_deferred.push_back(std::move(f)); }

// ================================================================== Control
Control* Control::create()
{
    auto c = new Control();
    if (c->init()) { c->autorelease(); return c; }
    delete c;
    return nullptr;
}

bool Control::init()
{
    if (!Node::init()) return false;
    setCascadeOpacityEnabled(true);
    setCascadeColorEnabled(true);
    setAnchorPoint(Vec2::ZERO);
    _seq = ++g_seq;
    return true;
}

void Control::addChild(Node* child, int z, int tag)
{
    if (auto c = dynamic_cast<Control*>(child)) c->_seq = ++g_seq;
    Node::addChild(child, z, tag);
    g_dirty = true;
}
void Control::addChild(Node* child, int z, std::string_view name)
{
    if (auto c = dynamic_cast<Control*>(child)) c->_seq = ++g_seq;
    Node::addChild(child, z, name);
    g_dirty = true;
}
void Control::removeChild(Node* child, bool cleanup)
{
    Node::removeChild(child, cleanup);
    g_dirty = true;
}

std::vector<Control*> Control::children() const
{
    std::vector<Control*> out;
    for (auto n : getChildren())
        if (auto c = dynamic_cast<Control*>(n)) out.push_back(c);
    std::sort(out.begin(), out.end(), [](Control* a, Control* b) { return a->_seq < b->_seq; });
    return out;
}

Control* Control::find(const std::string& n) const
{
    for (auto c : children())
    {
        if (c->getName() == n) return c;
        if (auto f = c->find(n)) return f;
    }
    return nullptr;
}

void Control::move_child(Control* c, int index)
{
    auto kids = children();
    kids.erase(std::remove(kids.begin(), kids.end(), c), kids.end());
    if (index < 0 || index > (int)kids.size()) index = (int)kids.size();
    kids.insert(kids.begin() + index, c);
    for (auto k : kids) k->_seq = ++g_seq;
    g_dirty = true;
}

void Control::clear_children()
{
    for (auto c : children()) c->removeFromParent();
    g_dirty = true;
}

void Control::queue_free()
{
    retain();
    Director::getInstance()->getScheduler()->runOnAxmolThread([this] {
        removeFromParent();
        release();
    });
}

void Control::onExit()
{
    tree_exiting.emit();
    Node::onExit();
}

void Control::set_position(const Vec2& p) { if (p != _pos) { _pos = p; apply_transform(); g_dirty = true; } }
void Control::set_size(const Vec2& s)
{
    if (s != _size)
    {
        _size = s;
        setContentSize(s);
        apply_transform();
        size_changed();
        resized.emit();
        g_dirty = true;
    }
}
void Control::set_custom_min(const Vec2& s) { if (s != _custom_min) { _custom_min = s; g_dirty = true; } }
void Control::set_h_flags(int f) { _hflags = f; g_dirty = true; }
void Control::set_v_flags(int f) { _vflags = f; g_dirty = true; }
void Control::set_pivot(const Vec2& p) { _pivot = p; apply_transform(); }
void Control::set_shift(const Vec2& s) { _shift = s; apply_transform(); }
void Control::setVisible(bool v)
{
    if (v != isVisible()) g_dirty = true;
    Node::setVisible(v);
}
bool Control::is_visible_in_tree() const
{
    for (const Node* n = this; n; n = n->getParent())
        if (!n->isVisible()) return false;
    return _running;
}

void Control::set_modulate(const Col& c)
{
    _modulate = c;
    setColor(c.c3b());
    setOpacity(u8(c.a));
}

void Control::set_anchor(Side s, float v) { _anchor[s] = v; _anchored = true; g_dirty = true; }
void Control::set_offset(Side s, float v) { _offset[s] = v; _anchored = true; g_dirty = true; }
void Control::set_offsets(float l, float t, float r, float b)
{
    _offset[0] = l; _offset[1] = t; _offset[2] = r; _offset[3] = b;
    _anchored = true;
    g_dirty = true;
}
void Control::set_grow(Grow h, Grow v) { _grow_h = h; _grow_v = v; g_dirty = true; }

void Control::set_anchors_preset(Preset p)
{
    float l = 0, t = 0, r = 0, b = 0;
    Grow gh = GROW_END, gv = GROW_END;
    switch (p)
    {
    case PRESET_TOP_LEFT: break;
    case PRESET_TOP_RIGHT: l = r = 1; gh = GROW_BEGIN; break;
    case PRESET_BOTTOM_LEFT: t = b = 1; gv = GROW_BEGIN; break;
    case PRESET_BOTTOM_RIGHT: l = r = 1; t = b = 1; gh = gv = GROW_BEGIN; break;
    case PRESET_CENTER_LEFT: t = b = 0.5f; gv = GROW_BOTH; break;
    case PRESET_CENTER_TOP: l = r = 0.5f; gh = GROW_BOTH; break;
    case PRESET_CENTER_RIGHT: l = r = 1; t = b = 0.5f; gh = GROW_BEGIN; gv = GROW_BOTH; break;
    case PRESET_CENTER_BOTTOM: l = r = 0.5f; t = b = 1; gh = GROW_BOTH; gv = GROW_BEGIN; break;
    case PRESET_CENTER: l = r = t = b = 0.5f; gh = gv = GROW_BOTH; break;
    case PRESET_LEFT_WIDE: b = 1; break;
    case PRESET_TOP_WIDE: r = 1; break;
    case PRESET_RIGHT_WIDE: l = r = 1; b = 1; gh = GROW_BEGIN; break;
    case PRESET_BOTTOM_WIDE: t = b = 1; r = 1; gv = GROW_BEGIN; break;
    case PRESET_VCENTER_WIDE: t = b = 0.5f; r = 1; gv = GROW_BOTH; break;
    case PRESET_HCENTER_WIDE: l = r = 0.5f; b = 1; gh = GROW_BOTH; break;
    case PRESET_FULL_RECT: r = b = 1; break;
    }
    _anchor[0] = l; _anchor[1] = t; _anchor[2] = r; _anchor[3] = b;
    _grow_h = gh;
    _grow_v = gv;
    _anchored = true;
    g_dirty = true;
}

Rect2 Control::global_rect() const
{
    Vec2 p = _pos + _shift;
    for (const Node* n = getParent(); n; n = n->getParent())
        if (auto c = dynamic_cast<const Control*>(n)) p += c->_pos + c->_shift;
    return {p, _size};
}

float Control::min_w() { return std::max(_custom_min.x, content_min_w()); }
float Control::min_h(float w) { return std::max(_custom_min.y, content_min_h(w)); }

void Control::apply_transform()
{
    float ph = 0;
    if (auto p = parent_control()) ph = p->_size.y;
    else if (getParent()) ph = getParent()->getContentSize().y;
    Vec2 ap(_size.x > 0 ? _pivot.x / _size.x : 0, _size.y > 0 ? 1 - _pivot.y / _size.y : 0);
    setAnchorPoint(ap);
    Vec2 tl = _pos + _shift;
    setPosition(std::round(tl.x) + _pivot.x, ph - std::round(tl.y) - _size.y + (_size.y - _pivot.y));
}

void Control::fit(const Vec2& pos, const Vec2& size)
{
    _pos = pos;
    if (size != _size)
    {
        _size = size;
        setContentSize(size);
        size_changed();
        resized.emit();
    }
    apply_transform();
    layout_children();
}

void Control::fit_child_in(Control* c, const Rect2& r)
{
    Vec2 pos = r.position, sz = r.size;
    float mw = c->min_w();
    if (!(c->_hflags & SIZE_FILL))
    {
        sz.x = std::min(mw, r.size.x);
        if (c->_hflags & SIZE_SHRINK_CENTER) pos.x += std::floor((r.size.x - sz.x) / 2);
        else if (c->_hflags & SIZE_SHRINK_END) pos.x += r.size.x - sz.x;
    }
    sz.x = std::max(sz.x, mw);
    float mh = c->min_h(sz.x);
    if (!(c->_vflags & SIZE_FILL))
    {
        sz.y = std::min(mh, r.size.y);
        if (c->_vflags & SIZE_SHRINK_CENTER) pos.y += std::floor((r.size.y - sz.y) / 2);
        else if (c->_vflags & SIZE_SHRINK_END) pos.y += r.size.y - sz.y;
    }
    sz.y = std::max(sz.y, mh);
    c->fit(pos, sz);
}

void Control::layout_children()
{
    for (auto c : children())
    {
        if (c->_anchored)
        {
            float l = c->_anchor[0] * _size.x + c->_offset[0];
            float t = c->_anchor[1] * _size.y + c->_offset[1];
            float r = c->_anchor[2] * _size.x + c->_offset[2];
            float b = c->_anchor[3] * _size.y + c->_offset[3];
            float w = r - l, mw = c->min_w();
            if (w < mw)
            {
                float d = mw - w;
                if (c->_grow_h == GROW_BEGIN) l -= d;
                else if (c->_grow_h == GROW_BOTH) l -= d / 2;
                w = mw;
            }
            float h = b - t, mh = c->min_h(w);
            if (h < mh)
            {
                float d = mh - h;
                if (c->_grow_v == GROW_BEGIN) t -= d;
                else if (c->_grow_v == GROW_BOTH) t -= d / 2;
                h = mh;
            }
            c->fit(Vec2(l, t), Vec2(w, h));
        }
        else
        {
            float w = std::max(c->_size.x, c->min_w());
            c->fit(c->_pos, Vec2(w, std::max(c->_size.y, c->min_h(w))));
        }
    }
}

void Control::visit(Renderer* r, const Mat4& t, uint32_t flags)
{
    if (!_visible) return;
    if (!_clip)
    {
        Node::visit(r, t, flags);
        return;
    }
    auto before = r->nextCallbackCommand();
    before->init(_globalZOrder);
    before->func = [this] { before_clip(); };
    r->addCommand(before);
    Node::visit(r, t, flags);
    auto after_cmd = r->nextCallbackCommand();
    after_cmd->init(_globalZOrder);
    after_cmd->func = [this] { after_clip(); };
    r->addCommand(after_cmd);
}

void Control::before_clip()
{
    auto view = Director::getInstance()->getRenderView();
    auto renderer = Director::getInstance()->getRenderer();
    _scissor_was_on = renderer->getScissorTest();
    if (_scissor_was_on) _scissor_saved = view->getScissorRect();
    Vec2 a = convertToWorldSpace(Vec2::ZERO), b = convertToWorldSpace(Vec2(_size.x, _size.y));
    ax::Rect mine(std::min(a.x, b.x), std::min(a.y, b.y), std::abs(b.x - a.x), std::abs(b.y - a.y));
    if (_scissor_was_on)
    {
        float x0 = std::max(mine.getMinX(), _scissor_saved.getMinX()), y0 = std::max(mine.getMinY(), _scissor_saved.getMinY());
        float x1 = std::min(mine.getMaxX(), _scissor_saved.getMaxX()), y1 = std::min(mine.getMaxY(), _scissor_saved.getMaxY());
        mine = ax::Rect(x0, y0, std::max(0.0f, x1 - x0), std::max(0.0f, y1 - y0));
    }
    renderer->setScissorTest(true);
    view->setScissorInPoints(mine.origin.x, mine.origin.y, mine.size.width, mine.size.height);
}

void Control::after_clip()
{
    auto renderer = Director::getInstance()->getRenderer();
    if (_scissor_was_on)
        Director::getInstance()->getRenderView()->setScissorInPoints(_scissor_saved.origin.x, _scissor_saved.origin.y,
                                                                     _scissor_saved.size.width, _scissor_saved.size.height);
    else
        renderer->setScissorTest(false);
}

// ================================================================== Node2D
Node2D* Node2D::create()
{
    auto c = new Node2D();
    if (c->init()) { c->autorelease(); return c; }
    delete c;
    return nullptr;
}
bool Node2D::init()
{
    if (!Control::init()) return false;
    mouse_filter = MOUSE_IGNORE;
    return true;
}
Node* Node2D::add2d(Node* n, const Vec2& p, int z)
{
    n->setPosition(p2(p));
    addChild(n, z);
    return n;
}

// ================================================================== containers
static std::vector<Control*> visible_kids(const Control* c)
{
    std::vector<Control*> out;
    for (auto k : c->children())
        if (k->isVisible()) out.push_back(k);
    return out;
}

#define GD_CREATE(T, ...)                                   \
    auto c = new T();                                       \
    if (!c->init()) { delete c; return nullptr; }           \
    c->autorelease();

BoxContainer* BoxContainer::create(bool v, int sep)
{
    GD_CREATE(BoxContainer)
    c->vertical = v;
    c->separation = sep;
    return c;
}
bool BoxContainer::init()
{
    if (!Control::init()) return false;
    mouse_filter = MOUSE_PASS;
    return true;
}

float BoxContainer::content_min_w()
{
    auto kids = visible_kids(this);
    float s = 0;
    for (auto k : kids) s = vertical ? std::max(s, k->min_w()) : s + k->min_w();
    if (!vertical && kids.size() > 1) s += separation * (kids.size() - 1);
    return s;
}

// along-axis sizes (Godot BoxContainer stretch algorithm)
std::vector<float> BoxContainer::distribute(const std::vector<Control*>& kids, float total, float* start)
{
    size_t n = kids.size();
    std::vector<float> mins(n), out(n);
    std::vector<bool> stretch(n);
    float cross = vertical ? _size.x : 0;
    float min_total = 0, ratio = 0;
    for (size_t i = 0; i < n; ++i)
    {
        auto k = kids[i];
        if (vertical)
        {
            float w = (k->h_flags() & SIZE_FILL) ? std::max(cross, k->min_w()) : k->min_w();
            mins[i] = k->min_h(w);
        }
        else
            mins[i] = k->min_w();
        stretch[i] = ((vertical ? k->v_flags() : k->h_flags()) & SIZE_EXPAND) != 0;
        min_total += mins[i];
        if (stretch[i]) ratio += k->stretch_ratio;
    }
    float seps = n > 1 ? separation * float(n - 1) : 0;
    float avail = total - seps;
    *start = 0;
    if (ratio > 0 && avail > min_total)
    {
        // iteratively give stretchers their share; those whose minimum is larger keep the minimum
        std::vector<bool> fixed(n, false);
        for (int pass = 0; pass < 8; ++pass)
        {
            float free = avail, r = 0;
            for (size_t i = 0; i < n; ++i)
                if (!stretch[i] || fixed[i]) free -= mins[i];
                else r += kids[i]->stretch_ratio;
            bool changed = false;
            for (size_t i = 0; i < n; ++i)
                if (stretch[i] && !fixed[i])
                {
                    float share = r > 0 ? free * kids[i]->stretch_ratio / r : 0;
                    if (share < mins[i]) { fixed[i] = true; changed = true; }
                    out[i] = share;
                }
            if (!changed) break;
        }
        for (size_t i = 0; i < n; ++i)
            if (!stretch[i] || fixed[i]) out[i] = mins[i];
        // rounding: floor each, give the remainder to the last stretcher
        float used = 0;
        int last = -1;
        for (size_t i = 0; i < n; ++i)
        {
            out[i] = std::floor(out[i]);
            used += out[i];
            if (stretch[i]) last = (int)i;
        }
        if (last >= 0) out[last] += std::max(0.0f, avail - used);
    }
    else
    {
        out = mins;
        float extra = avail - min_total;
        if (extra > 0)
        {
            if (alignment == ALIGNMENT_CENTER) *start = std::floor(extra / 2);
            else if (alignment == ALIGNMENT_END) *start = extra;
        }
    }
    return out;
}

float BoxContainer::content_min_h(float w)
{
    auto kids = visible_kids(this);
    if (kids.empty()) return 0;
    if (vertical)
    {
        float s = separation * float(kids.size() - 1);
        for (auto k : kids)
        {
            float cw = (k->h_flags() & SIZE_FILL) ? std::max(w, k->min_w()) : k->min_w();
            s += k->min_h(cw);
        }
        return s;
    }
    Vec2 saved = _size;
    _size.x = w;
    float st;
    auto ws = distribute(kids, w, &st);
    _size = saved;
    float h = 0;
    for (size_t i = 0; i < kids.size(); ++i) h = std::max(h, kids[i]->min_h(std::max(ws[i], kids[i]->min_w())));
    return h;
}

void BoxContainer::layout_children()
{
    auto kids = visible_kids(this);
    float start;
    auto sizes = distribute(kids, vertical ? _size.y : _size.x, &start);
    float p = start;
    for (size_t i = 0; i < kids.size(); ++i)
    {
        Rect2 r = vertical ? Rect2{Vec2(0, p), Vec2(_size.x, sizes[i])} : Rect2{Vec2(p, 0), Vec2(sizes[i], _size.y)};
        fit_child_in(kids[i], r);
        p += sizes[i] + separation;
    }
}

GridContainer* GridContainer::create(int cols)
{
    GD_CREATE(GridContainer)
    c->columns = std::max(1, cols);
    return c;
}
bool GridContainer::init()
{
    if (!Control::init()) return false;
    mouse_filter = MOUSE_PASS;
    return true;
}

void GridContainer::measure(float width, std::vector<float>& cols, std::vector<float>& rows)
{
    auto kids = visible_kids(this);
    int nc = std::max(1, columns);
    int nr = kids.empty() ? 0 : int((kids.size() + nc - 1) / nc);
    nc = std::min<int>(nc, std::max<int>(1, (int)kids.size()));
    cols.assign(nc, 0);
    std::vector<bool> expand(nc, false);
    for (size_t i = 0; i < kids.size(); ++i)
    {
        int c = int(i) % nc;
        cols[c] = std::max(cols[c], kids[i]->min_w());
        if (kids[i]->h_flags() & SIZE_EXPAND) expand[c] = true;
    }
    if (width > 0)
    {
        float min_sum = h_separation * float(nc - 1);
        for (float c : cols) min_sum += c;
        int ne = (int)std::count(expand.begin(), expand.end(), true);
        float extra = width - min_sum;
        if (ne > 0 && extra > 0)
        {
            // Godot: expanded columns get an equal share of (width - fixed columns), never below their minimum
            float fixed = h_separation * float(nc - 1);
            for (int c = 0; c < nc; ++c) if (!expand[c]) fixed += cols[c];
            float share = std::floor((width - fixed) / ne);
            for (int c = 0; c < nc; ++c) if (expand[c]) cols[c] = std::max(cols[c], share);
        }
    }
    rows.assign(nr, 0);
    for (size_t i = 0; i < kids.size(); ++i)
    {
        int c = int(i) % nc, r = int(i) / nc;
        float cw = (kids[i]->h_flags() & SIZE_FILL) ? cols[c] : kids[i]->min_w();
        rows[r] = std::max(rows[r], kids[i]->min_h(cw));
    }
}

float GridContainer::content_min_w()
{
    std::vector<float> c, r;
    measure(0, c, r);
    float s = c.empty() ? 0 : h_separation * float(c.size() - 1);
    for (float v : c) s += v;
    return s;
}

float GridContainer::content_min_h(float w)
{
    std::vector<float> c, r;
    measure(w, c, r);
    float s = r.empty() ? 0 : v_separation * float(r.size() - 1);
    for (float v : r) s += v;
    return s;
}

void GridContainer::layout_children()
{
    auto kids = visible_kids(this);
    std::vector<float> cols, rows;
    measure(_size.x, cols, rows);
    if (cols.empty()) return;
    int nc = (int)cols.size();
    // expanded rows share the extra height
    std::vector<bool> rexp(rows.size(), false);
    for (size_t i = 0; i < kids.size(); ++i)
        if (kids[i]->v_flags() & SIZE_EXPAND) rexp[i / nc] = true;
    float used = rows.empty() ? 0 : v_separation * float(rows.size() - 1);
    for (float r : rows) used += r;
    int ne = (int)std::count(rexp.begin(), rexp.end(), true);
    if (ne > 0 && _size.y > used)
        for (size_t r = 0; r < rows.size(); ++r)
            if (rexp[r]) rows[r] += std::floor((_size.y - used) / ne);
    float y = 0;
    for (size_t r = 0; r < rows.size(); ++r)
    {
        float x = 0;
        for (int c = 0; c < nc; ++c)
        {
            size_t i = r * nc + c;
            if (i >= kids.size()) break;
            fit_child_in(kids[i], {Vec2(x, y), Vec2(cols[c], rows[r])});
            x += cols[c] + h_separation;
        }
        y += rows[r] + v_separation;
    }
}

FlowContainer* FlowContainer::create() { GD_CREATE(FlowContainer) return c; }
bool FlowContainer::init()
{
    if (!Control::init()) return false;
    mouse_filter = MOUSE_PASS;
    return true;
}
float FlowContainer::content_min_w()
{
    float m = 0;
    for (auto k : visible_kids(this)) m = std::max(m, k->min_w());
    return m;
}
float FlowContainer::flow(float width, bool apply)
{
    auto kids = visible_kids(this);
    float y = 0;
    size_t i = 0;
    while (i < kids.size())
    {
        size_t j = i;
        float x = 0, h = 0;
        while (j < kids.size())
        {
            float w = kids[j]->min_w();
            if (j > i && x + w > width) break;
            x += w + h_separation;
            h = std::max(h, kids[j]->min_h(w));
            ++j;
        }
        if (apply)
        {
            float line_w = x - h_separation, off = 0;
            if (alignment == ALIGNMENT_CENTER) off = std::floor((width - line_w) / 2);
            else if (alignment == ALIGNMENT_END) off = width - line_w;
            float px = off;
            for (size_t k = i; k < j; ++k)
            {
                float w = kids[k]->min_w();
                fit_child_in(kids[k], {Vec2(px, y), Vec2(w, h)});
                px += w + h_separation;
            }
        }
        y += h + v_separation;
        i = j;
    }
    return kids.empty() ? 0 : y - v_separation;
}
float FlowContainer::content_min_h(float w) { return flow(w, false); }
void FlowContainer::layout_children() { flow(_size.x, true); }

CenterContainer* CenterContainer::create() { GD_CREATE(CenterContainer) return c; }
bool CenterContainer::init()
{
    if (!Control::init()) return false;
    mouse_filter = MOUSE_PASS;
    return true;
}
float CenterContainer::content_min_w()
{
    float m = 0;
    for (auto k : visible_kids(this)) m = std::max(m, k->min_w());
    return m;
}
float CenterContainer::content_min_h(float)
{
    float m = 0;
    for (auto k : visible_kids(this)) m = std::max(m, k->combined_min().y);
    return m;
}
void CenterContainer::layout_children()
{
    for (auto k : visible_kids(this))
    {
        Vec2 m = k->combined_min();
        k->fit(Vec2(std::floor((_size.x - m.x) / 2), std::floor((_size.y - m.y) / 2)), m);
    }
}

MarginContainer* MarginContainer::create(float l, float t, float r, float b)
{
    GD_CREATE(MarginContainer)
    c->margin[0] = l; c->margin[1] = t; c->margin[2] = r; c->margin[3] = b;
    return c;
}
bool MarginContainer::init()
{
    if (!Control::init()) return false;
    mouse_filter = MOUSE_PASS;
    return true;
}
float MarginContainer::content_min_w()
{
    float m = 0;
    for (auto k : visible_kids(this)) m = std::max(m, k->min_w());
    return m + margin[0] + margin[2];
}
float MarginContainer::content_min_h(float w)
{
    float m = 0, iw = w - margin[0] - margin[2];
    for (auto k : visible_kids(this)) m = std::max(m, k->min_h((k->h_flags() & SIZE_FILL) ? std::max(iw, k->min_w()) : k->min_w()));
    return m + margin[1] + margin[3];
}
void MarginContainer::layout_children()
{
    Rect2 r{Vec2(margin[0], margin[1]), Vec2(_size.x - margin[0] - margin[2], _size.y - margin[1] - margin[3])};
    for (auto k : visible_kids(this)) fit_child_in(k, r);
}

// ================================================================== StyleBox
StyleBox StyleBox::tex(const std::string& path, float margin, float content)
{
    StyleBox s;
    s.kind = TEXTURE;
    s.texture = path;
    for (int i = 0; i < 4; ++i) { s.tex_margin[i] = margin; s.content_margin[i] = content; }
    return s;
}
StyleBox StyleBox::flat(const Col& bg, const Col& border, float bw)
{
    StyleBox s;
    s.kind = FLAT;
    s.bg = bg;
    s.border = border;
    s.border_width = bw;
    return s;
}

static void flat_children(Node* n, const StyleBox& sb, const Vec2& size)
{
    n->removeAllChildren();
    auto rect = [&](float x, float y, float w, float h, const Col& c) {   // y from the top
        if (w <= 0 || h <= 0 || c.a <= 0) return;
        auto s = Sprite::createWithTexture(white_texture());
        s->setTextureRect(ax::Rect(0, 0, 4, 4));
        s->setAnchorPoint(Vec2::ZERO);
        s->setScale(w / 4, h / 4);
        s->setPosition(x, size.y - y - h);
        s->setColor(c.c3b());
        s->setOpacity(u8(c.a));
        n->addChild(s);
    };
    float b = sb.border_width;
    rect(0, 0, size.x, size.y, sb.bg);
    if (b > 0)
    {
        rect(0, 0, size.x, b, sb.border);
        rect(0, size.y - b, size.x, b, sb.border);
        rect(0, b, b, size.y - 2 * b, sb.border);
        rect(size.x - b, b, b, size.y - 2 * b, sb.border);
    }
}

Node* StyleBox::build(const Vec2& size) const
{
    Node* n = nullptr;
    if (kind == TEXTURE)
    {
        if (auto t = gd::texture(texture))
        {
            Vec2 ts = t->getContentSize();
            ax::Rect caps(tex_margin[0], tex_margin[1], std::max(1.0f, ts.x - tex_margin[0] - tex_margin[2]),
                          std::max(1.0f, ts.y - tex_margin[1] - tex_margin[3]));
            std::string key = texture.rfind("res://", 0) == 0 ? texture.substr(6) : texture;
            auto s9 = ax::ui::Scale9Sprite::create(caps, key);
            if (s9)
            {
                s9->setColor(modulate.c3b());
                s9->setOpacity(u8(modulate.a));
                n = s9;
            }
        }
    }
    if (!n) n = Node::create();
    n->setCascadeOpacityEnabled(true);
    n->setAnchorPoint(Vec2::ZERO);
    resize(n, *this, size);
    return n;
}

void StyleBox::resize(Node* n, const StyleBox& sb, const Vec2& size)
{
    if (!n) return;
    if (sb.kind == FLAT) flat_children(n, sb, size);
    n->setContentSize(size);
}

// ================================================================== Panel
Panel* Panel::create(const StyleBox& sb)
{
    GD_CREATE(Panel)
    c->set_style(sb);
    return c;
}
bool Panel::init() { return Control::init(); }
void Panel::set_style(const StyleBox& sb)
{
    _style = sb;
    if (_bg) _bg->removeFromParent();
    _bg = sb.build(_size);
    Node::addChild(_bg, -10000);
    g_dirty = true;
}
void Panel::size_changed() { StyleBox::resize(_bg, _style, _size); }

PanelContainer* PanelContainer::create(const StyleBox& sb)
{
    GD_CREATE(PanelContainer)
    c->set_style(sb);
    return c;
}
bool PanelContainer::init()
{
    if (!Panel::init()) return false;
    return true;
}
float PanelContainer::content_min_w()
{
    float m = 0;
    for (auto k : visible_kids(this)) m = std::max(m, k->min_w());
    return m + _style.cw();
}
float PanelContainer::content_min_h(float w)
{
    float m = 0, iw = w - _style.cw();
    for (auto k : visible_kids(this)) m = std::max(m, k->min_h((k->h_flags() & SIZE_FILL) ? std::max(iw, k->min_w()) : k->min_w()));
    return m + _style.ch();
}
void PanelContainer::layout_children()
{
    Rect2 r{Vec2(_style.content_margin[0], _style.content_margin[1]), Vec2(_size.x - _style.cw(), _size.y - _style.ch())};
    for (auto k : visible_kids(this)) fit_child_in(k, r);
}

// ================================================================== Label
Label* Label::create(const std::string& text, int font_size)
{
    GD_CREATE(Label)
    c->_font_size = font_size;
    c->_text = text;
    c->rebuild();
    return c;
}
bool Label::init()
{
    if (!Control::init()) return false;
    mouse_filter = MOUSE_IGNORE;
    return true;
}
void Label::mark() { g_dirty = true; size_changed(); }
void Label::set_text(const std::string& t) { if (t != _text) { _text = t; if (_lbl) _lbl->setString(t); mark(); } }
void Label::set_font_size(int s) { if (s != _font_size) { _font_size = s; rebuild(); } }
void Label::set_color(const Col& c) { _color = c; if (_lbl) { _lbl->setTextColor(c.c4b()); } }
void Label::set_shadow(const Col& c, float off) { _shadow = c; _shadow_off = off; rebuild(); }
void Label::set_outline(int size, const Col& c) { _outline = size; _outline_col = c; rebuild(); }

void Label::rebuild()
{
    if (_lbl) _lbl->removeFromParent();
    _lbl = make_label(_font_size, _outline, _outline_col);
    _lbl->setLineSpacing((float)line_spacing);
    _lbl->setTextColor(_color.c4b());
    if (_shadow_off > 0 && _shadow.a > 0) _lbl->enableShadow(_shadow.c4b(), ax::Size(_shadow_off, -_shadow_off), 0);
    _lbl->setString(_text);
    Node::addChild(_lbl);
    mark();
}

Vec2 Label::text_size() const { return gd::text_size(_text, _font_size, 0, _outline); }

float Label::content_min_w()
{
    if (_wrap || _clip_text) return 0;
    return std::ceil(gd::text_size(_text, _font_size, 0, _outline).x);
}
float Label::content_min_h(float w)
{
    if (_wrap) return std::ceil(gd::text_size(_text.empty() ? " " : _text, _font_size, std::max(1.0f, w), _outline).y);
    return std::ceil(gd::text_size(" ", _font_size, 0, _outline).y);
}

static size_t utf8_prefix(const std::string& s, size_t chars)
{
    size_t i = 0, n = 0;
    while (i < s.size() && n < chars)
    {
        unsigned char c = s[i];
        i += c < 0x80 ? 1 : c < 0xE0 ? 2 : c < 0xF0 ? 3 : 4;
        ++n;
    }
    return std::min(i, s.size());
}
static size_t utf8_len(const std::string& s)
{
    size_t n = 0;
    for (unsigned char c : s) n += (c & 0xC0) != 0x80;
    return n;
}

void Label::set_visible_ratio(float r)
{
    _visible_ratio = std::clamp(r, 0.0f, 1.0f);
    size_changed();
}

void Label::size_changed()
{
    if (!_lbl) return;
    std::string shown = _text;
    if (_visible_ratio < 1) shown = _text.substr(0, utf8_prefix(_text, size_t(std::floor(utf8_len(_text) * _visible_ratio))));
    TextHAlignment ha = h_align == ALIGN_CENTER ? TextHAlignment::CENTER : h_align == ALIGN_RIGHT ? TextHAlignment::RIGHT : TextHAlignment::LEFT;
    if (_wrap)
    {
        _lbl->setDimensions(std::max(1.0f, _size.x), 0);
        _lbl->setAlignment(ha, TextVAlignment::TOP);
        _lbl->setString(shown);
        // keep layout stable while typing: measure with the full text
        float h = gd::text_size(_text.empty() ? " " : _text, _font_size, std::max(1.0f, _size.x), _outline).y;
        float lh = _lbl->getContentSize().y;
        float top = v_align == VALIGN_CENTER ? std::floor((_size.y - h) / 2) : v_align == VALIGN_BOTTOM ? _size.y - h : 0;
        _lbl->setPosition(0, std::round(_size.y - top - lh));
        return;
    }
    _lbl->setDimensions(0, 0);
    _lbl->setAlignment(ha, TextVAlignment::TOP);
    std::string s = shown;
    if (_clip_text && gd::text_size(s, _font_size, 0, _outline).x > _size.x)
    {
        size_t n = utf8_len(s);
        while (n > 0 && gd::text_size(s.substr(0, utf8_prefix(s, n)) + "...", _font_size, 0, _outline).x > _size.x) --n;
        s = s.substr(0, utf8_prefix(s, n)) + "...";
    }
    _lbl->setString(s);
    ax::Size ts = _lbl->getContentSize();
    float full_w = gd::text_size(_text, _font_size, 0, _outline).x;
    float w = _visible_ratio < 1 ? std::min(full_w, _size.x) : ts.x;
    float x = h_align == ALIGN_CENTER ? std::floor((_size.x - w) / 2) : h_align == ALIGN_RIGHT ? _size.x - w : 0;
    float top = v_align == VALIGN_CENTER ? std::floor((_size.y - ts.y) / 2) : v_align == VALIGN_BOTTOM ? _size.y - ts.y : 0;
    _lbl->setPosition(std::round(x), std::round(_size.y - top - ts.y));
}

// ================================================================== TextureRect
TextureRect* TextureRect::create(const std::string& path)
{
    GD_CREATE(TextureRect)
    c->set_texture(path);
    return c;
}
bool TextureRect::init()
{
    if (!Control::init()) return false;
    mouse_filter = MOUSE_IGNORE;
    return true;
}
void TextureRect::set_texture(const std::string& path)
{
    _path = path;
    set_texture(gd::texture(path));
}
void TextureRect::set_texture(Texture2D* t)
{
    _tex = t;
    if (_spr) { _spr->removeFromParent(); _spr = nullptr; }
    if (t)
    {
        _spr = Sprite::createWithTexture(t);
        _spr->setAnchorPoint(Vec2::ZERO);
        Node::addChild(_spr);
    }
    g_dirty = true;
    size_changed();
}
void TextureRect::set_region(const ax::Rect& r)
{
    _region = r;
    _has_region = true;
    g_dirty = true;
    size_changed();
}
Vec2 TextureRect::texture_size() const
{
    if (!_tex) return Vec2::ZERO;
    return _has_region ? Vec2(_region.size.width, _region.size.height) : Vec2(_tex->getContentSize());
}
float TextureRect::content_min_w() { return ignore_size ? 0 : texture_size().x; }
float TextureRect::content_min_h(float) { return ignore_size ? 0 : texture_size().y; }

void TextureRect::size_changed()
{
    if (!_spr || !_tex) return;
    Vec2 ts = texture_size();
    if (ts.x <= 0 || ts.y <= 0) return;
    ax::Rect base = _has_region ? _region : ax::Rect(0, 0, ts.x, ts.y);
    _spr->setFlippedX(flip_h);
    _spr->setFlippedY(flip_v);
    _spr->setBlendFunc(additive ? BlendFunc::ADDITIVE : _spr->getTexture()->hasPremultipliedAlpha() ? BlendFunc::ALPHA_PREMULTIPLIED : BlendFunc::ALPHA_NON_PREMULTIPLIED);
    Vec2 sz = _size;
    float sx = 1, sy = 1, x = 0, top = 0;
    ax::Rect rect = base;
    switch (stretch)
    {
    case STRETCH_SCALE: sx = sz.x / ts.x; sy = sz.y / ts.y; break;
    case STRETCH_TILE:
    {
        Texture2D::TexParams p(backend::SamplerFilter::NEAREST, backend::SamplerFilter::NEAREST,
                               backend::SamplerAddressMode::REPEAT, backend::SamplerAddressMode::REPEAT);
        _tex->setTexParameters(p);
        rect = ax::Rect(0, 0, sz.x, sz.y);
        break;
    }
    case STRETCH_KEEP: break;
    case STRETCH_KEEP_CENTERED: x = std::floor((sz.x - ts.x) / 2); top = std::floor((sz.y - ts.y) / 2); break;
    case STRETCH_KEEP_ASPECT:
    case STRETCH_KEEP_ASPECT_CENTERED:
    {
        float k = std::min(sz.x / ts.x, sz.y / ts.y);
        sx = sy = k;
        if (stretch == STRETCH_KEEP_ASPECT_CENTERED)
        {
            x = std::floor((sz.x - ts.x * k) / 2);
            top = std::floor((sz.y - ts.y * k) / 2);
        }
        break;
    }
    case STRETCH_KEEP_ASPECT_COVERED:
    {
        float k = std::max(sz.x / ts.x, sz.y / ts.y);
        sx = sy = k;
        float vw = sz.x / k, vh = sz.y / k;
        rect = ax::Rect(base.origin.x + (ts.x - vw) / 2, base.origin.y + (ts.y - vh) / 2, vw, vh);
        break;
    }
    }
    _spr->setTextureRect(rect);
    _spr->setScale(sx, sy);
    float h = rect.size.height * sy;
    _spr->setPosition(x, _size.y - top - h);
    _spr->setVisible(sz.x > 0 && sz.y > 0);
}

// ================================================================== ColorRect
ColorRect* ColorRect::create(const Col& col)
{
    GD_CREATE(ColorRect)
    c->set_color(col);
    return c;
}
bool ColorRect::init()
{
    if (!Control::init()) return false;
    _spr = Sprite::createWithTexture(white_texture());
    _spr->setTextureRect(ax::Rect(0, 0, 4, 4));
    _spr->setAnchorPoint(Vec2::ZERO);
    Node::addChild(_spr, -10000);
    return true;
}
void ColorRect::set_color(const Col& c)
{
    _color = c;
    _spr->setColor(c.c3b());
    _spr->setOpacity(u8(c.a));
}
void ColorRect::size_changed()
{
    _spr->setScale(_size.x / 4, _size.y / 4);
    _spr->setBlendFunc(additive ? BlendFunc::ADDITIVE : _spr->getTexture()->hasPremultipliedAlpha() ? BlendFunc::ALPHA_PREMULTIPLIED : BlendFunc::ALPHA_NON_PREMULTIPLIED);
}

// ================================================================== buttons
bool BaseButton::init()
{
    if (!Control::init()) return false;
    mouse_filter = MOUSE_STOP;
    return true;
}
void BaseButton::set_disabled(bool d)
{
    _disabled = d;
    if (d) _down = false;
    update_look();
}
void BaseButton::on_hover(bool inside)
{
    _hover = inside;
    update_look();
}
void BaseButton::on_gui_event(InputEvent& e)
{
    if (_disabled)
    {
        if (e.type == Ev::PRESS) e.accept();
        return;
    }
    switch (e.type)
    {
    case Ev::PRESS:
        e.accept();
        if (press_cooldown > 0 && ticks() - _last_press < press_cooldown) return;
        _down = true;
        update_look();
        button_down.emit();
        break;
    case Ev::RELEASE:
    {
        if (!_down) return;
        _down = false;
        update_look();
        button_up.emit();
        Rect2 r{Vec2::ZERO, _size};
        if (r.has_point(e.local))
        {
            _last_press = ticks();
            retain();   // a handler may free this button
            pressed.emit();
            release();
        }
        e.accept();
        break;
    }
    case Ev::CANCEL:
        if (_down)
        {
            _down = false;
            update_look();
            button_up.emit();
        }
        break;
    default: break;
    }
}

Button* Button::create(const std::string& text)
{
    GD_CREATE(Button)
    c->set_text(text);
    return c;
}
bool Button::init()
{
    if (!BaseButton::init()) return false;
    _font_colors[NORMAL] = Col::WHITE;
    _font_colors[HOVER] = Col("#fff6d0");
    _font_colors[PRESSED] = Col("#e0d8c8");
    _font_colors[DISABLED] = Col("#8a8690");
    _label = Label::create("", _font_size);
    _label->set_outline(10, Col("#120a0c"));
    _label->set_align(ALIGN_CENTER, VALIGN_CENTER);
    Node::addChild(_label, 1);
    _label->set_name("__label");
    return true;
}
void Button::set_text(const std::string& t) { _text = t; _label->set_text(t); _label->setVisible(!t.empty()); g_dirty = true; }
void Button::set_icon(const std::string& path)
{
    _icon_path = path;
    if (!_icon)
    {
        _icon = TextureRect::create();
        _icon->ignore_size = true;
        _icon->stretch = STRETCH_KEEP_ASPECT_CENTERED;
        Node::addChild(_icon, 1);
        _icon->set_name("__icon");
    }
    _icon->set_texture(path);
    _icon->setVisible(_icon->texture() != nullptr);
    g_dirty = true;
}
void Button::set_font_size(int s) { _font_size = s; _label->set_font_size(s); }
void Button::set_style(State s, const StyleBox& sb) { _styles[s] = sb; _bg_state = STATE_COUNT; update_look(); g_dirty = true; }
void Button::set_font_color(State s, const Col& c) { _font_colors[s] = c; update_look(); }
void Button::set_outline(int size, const Col& c) { _label->set_outline(size, c); }

Button::State Button::state() const
{
    if (_disabled) return DISABLED;
    if (_down) return PRESSED;
    if (_hover) return HOVER;
    return NORMAL;
}

Vec2 Button::icon_draw_size(float avail_h)
{
    if (!_icon || !_icon->isVisible()) return Vec2::ZERO;
    Vec2 ts = _icon->texture_size();
    if (ts.x <= 0) return Vec2::ZERO;
    float w = icon_max_width > 0 ? std::min<float>((float)icon_max_width, avail_h > 0 ? avail_h : (float)icon_max_width) : ts.x;
    return Vec2(w, ts.y * w / ts.x);
}

float Button::content_min_w()
{
    const StyleBox& sb = _styles[NORMAL];
    float tw = _text.empty() ? 0 : std::ceil(gd::text_size(_text, _font_size, 0, _label->outline()).x);
    Vec2 is = icon_draw_size(0);
    if (icon_top) return sb.cw() + std::max(tw, is.x);
    return sb.cw() + tw + is.x + (tw > 0 && is.x > 0 ? h_separation : 0);
}
float Button::content_min_h(float)
{
    const StyleBox& sb = _styles[NORMAL];
    float th = _text.empty() ? 0 : std::ceil(gd::text_size(_text, _font_size, 0, _label->outline()).y);
    if (icon_top) return sb.ch() + th + icon_draw_size(0).y + (th > 0 ? 4 : 0);
    return sb.ch() + std::max(th, icon_draw_size(0).y);
}

void Button::update_look()
{
    State s = state();
    const StyleBox& sb = _styles[s].kind == StyleBox::EMPTY && s != NORMAL ? _styles[NORMAL] : _styles[s];
    if (_bg_state != s)
    {
        if (_bg) _bg->removeFromParent();
        _bg = sb.build(_size);
        Node::addChild(_bg, -10000);
        _bg_state = s;
    }
    _label->set_color(_font_colors[s]);
    size_changed();
}

void Button::size_changed()
{
    State s = state();
    const StyleBox& sb = _styles[s].kind == StyleBox::EMPTY && s != NORMAL ? _styles[NORMAL] : _styles[s];
    if (_bg) StyleBox::resize(_bg, sb, _size);
    // content: [icon] sep [text], centred in the content rect
    float cx = sb.content_margin[0], cy = sb.content_margin[1];
    float cw = _size.x - sb.cw(), ch = _size.y - sb.ch();
    if (icon_top)
    {
        float th = _text.empty() ? 0 : std::ceil(gd::text_size(_text, _font_size, 0, _label->outline()).y);
        Vec2 is = icon_draw_size(std::max(0.0f, ch - th - 4));
        if (_icon && _icon->isVisible()) _icon->fit(Vec2(cx + std::floor((cw - is.x) / 2), cy), is);
        _label->fit(Vec2(cx, cy + is.y + 4), Vec2(cw, std::max(th, ch - is.y - 4)));
        return;
    }
    Vec2 is = icon_draw_size(ch);
    float tw = _text.empty() ? 0 : std::ceil(gd::text_size(_text, _font_size, 0, _label->outline()).x);
    float total = is.x + tw + (is.x > 0 && tw > 0 ? h_separation : 0);
    float x = cx;
    if (alignment == ALIGN_CENTER) x = cx + std::floor((cw - total) / 2);
    else if (alignment == ALIGN_RIGHT) x = cx + cw - total;
    if (_icon && _icon->isVisible())
    {
        _icon->fit(Vec2(x, cy + std::floor((ch - is.y) / 2)), is);
        x += is.x + (tw > 0 ? h_separation : 0);
    }
    float tw_box = std::max(0.0f, std::min(tw, cx + cw - x));
    if (tw_box < tw) tw_box = tw;
    _label->fit(Vec2(x, cy), Vec2(tw_box, std::max(0.0f, ch)));
}

// ================================================================== ScrollContainer
ScrollContainer* ScrollContainer::create() { GD_CREATE(ScrollContainer) return c; }
bool ScrollContainer::init()
{
    if (!Control::init()) return false;
    mouse_filter = MOUSE_PASS;
    _clip = true;
    _bar = StyleBox::tex("assets/ui/p5_scroll.png", 6, 4).build(Vec2(12, 10));
    _grab = StyleBox::tex("assets/ui/p5_scroll_grab.png", 6, 4).build(Vec2(12, 10));
    Node::addChild(_bar, 10000);
    Node::addChild(_grab, 10001);
    scheduleUpdate();
    return true;
}
float ScrollContainer::content_min_w()
{
    float m = 0;
    for (auto k : visible_kids(this)) m = std::max(m, k->min_w());
    return m;
}
float ScrollContainer::max_scroll()
{
    auto kids = visible_kids(this);
    if (kids.empty()) return 0;
    return std::max(0.0f, kids[0]->size().y - _size.y);
}
void ScrollContainer::set_scroll_vertical(float v)
{
    float nv = std::clamp(v, 0.0f, max_scroll());
    if (nv != _scroll)
    {
        _scroll = nv;
        g_dirty = true;
        scrolled.emit();
    }
}
void ScrollContainer::layout_children()
{
    for (auto k : visible_kids(this))
    {
        // Godot: only EXPAND children grow to the scroll area's size
        float w = (k->h_flags() & SIZE_EXPAND) ? std::max(_size.x, k->min_w()) : k->min_w();
        float h = k->min_h(w);
        if (k->v_flags() & SIZE_EXPAND) h = std::max(h, _size.y);
        k->fit(Vec2(0, 0), Vec2(w, h));
        _scroll = std::clamp(_scroll, 0.0f, std::max(0.0f, h - _size.y));
        k->fit(Vec2(0, -std::round(_scroll)), Vec2(w, h));
    }
    place_bar();
}
void ScrollContainer::place_bar()
{
    float ms = max_scroll();
    bool on = show_bar && ms > 1 && _size.y > 40;
    _bar->setVisible(on);
    _grab->setVisible(on);
    if (!on) return;
    float track = _size.y - 8, content = _size.y + ms;
    float gh = std::max(40.0f, track * _size.y / content);
    float gy = (track - gh) * (_scroll / ms);
    StyleBox::resize(_bar, StyleBox(), Vec2(12, track));
    _bar->setPosition(_size.x - 12, 4);
    _grab->setContentSize(Vec2(12, gh));
    _grab->setPosition(_size.x - 12, _size.y - 4 - gy - gh);
}
void ScrollContainer::begin_drag(const Vec2& g)
{
    _dragging = true;
    _drag_y = g.y;
    _vel = 0;
    _last_move_t = ticks();
}
void ScrollContainer::on_gui_event(InputEvent& e)
{
    switch (e.type)
    {
    case Ev::PRESS:
        _vel = 0;
        break;
    case Ev::MOVE:
        if (_dragging)
        {
            float dy = e.global.y - _drag_y;
            _drag_y = e.global.y;
            double now = ticks();
            float dt = float(std::max(1e-3, now - _last_move_t));
            _last_move_t = now;
            _vel = -dy / dt;
            set_scroll_vertical(_scroll - dy);
            e.accept();
        }
        break;
    case Ev::RELEASE:
    case Ev::CANCEL:
        if (_dragging && ticks() - _last_move_t > 0.08) _vel = 0;
        _dragging = false;
        break;
    case Ev::WHEEL:
        _vel = 0;
        set_scroll_vertical(_scroll - e.wheel * 90);
        e.accept();
        break;
    }
}
void ScrollContainer::update(float dt)
{
    if (!_dragging && std::abs(_vel) > 5)
    {
        set_scroll_vertical(_scroll + _vel * dt);
        _vel *= std::pow(0.05f, dt);
        if (_scroll <= 0 || _scroll >= max_scroll()) _vel = 0;
    }
}
void ScrollContainer::ensure_visible(Control* c)
{
    if (!c) return;
    float top = c->global_rect().position.y - global_rect().position.y + _scroll;
    if (top < _scroll) set_scroll_vertical(top);
    else if (top + c->size().y > _scroll + _size.y) set_scroll_vertical(top + c->size().y - _size.y);
}

// ================================================================== HSlider
HSlider* HSlider::create(float mn, float mx, float st)
{
    GD_CREATE(HSlider)
    c->min_value = mn;
    c->max_value = mx;
    c->step = st;
    c->_value = mn;
    return c;
}
bool HSlider::init()
{
    if (!Control::init()) return false;
    _track = StyleBox::tex("assets/ui/v2_bar.png", 18, 10).build(Vec2(100, 36));
    _fill = StyleBox::tex("assets/ui/v2_fill_stat.png", 0, 0).build(Vec2(10, 12));
    Node::addChild(_track, -2);
    Node::addChild(_fill, -1);
    if (auto t = texture("assets/ui/p5_knob.png"))
    {
        _knob = Sprite::createWithTexture(t);
        Node::addChild(_knob, 1);
    }
    return true;
}
void HSlider::set_value(float v, bool emit)
{
    if (step > 0) v = min_value + std::round((v - min_value) / step) * step;
    v = std::clamp(v, min_value, max_value);
    bool changed = v != _value;
    _value = v;
    size_changed();
    if (changed && emit) value_changed.emit(v);
}
void HSlider::size_changed()
{
    float th = 36, cy = _size.y / 2;
    _track->setContentSize(Vec2(_size.x, th));
    _track->setPosition(0, cy - th / 2);
    float k = max_value > min_value ? (_value - min_value) / (max_value - min_value) : 0;
    float fw = std::max(0.0f, (_size.x - 24) * k);
    _fill->setContentSize(Vec2(fw, 12));
    _fill->setPosition(12, cy - 6);
    _fill->setVisible(fw > 1);
    if (_knob) _knob->setPosition(12 + (_size.x - 24) * k, cy);
}
void HSlider::on_gui_event(InputEvent& e)
{
    if (e.type == Ev::PRESS || e.type == Ev::MOVE)
    {
        float k = std::clamp((e.local.x - 12) / std::max(1.0f, _size.x - 24), 0.0f, 1.0f);
        set_value(min_value + k * (max_value - min_value));
        e.accept();
    }
}

// ================================================================== LineEdit
LineEdit* LineEdit::create(const std::string& text)
{
    GD_CREATE(LineEdit)
    c->set_text(text);
    return c;
}
bool LineEdit::init()
{
    if (!Control::init()) return false;
    _style = StyleBox::tex("assets/ui/v2_inset.png", 15, 18);
    _bg = _style.build(Vec2(10, 10));
    Node::addChild(_bg, -1);
    _field = TextFieldTTF::textFieldWithPlaceHolder("", font_path(), (float)font_size);
    _field->setAnchorPoint(Vec2::ZERO);
    _field->setTextColor(Col("#f4ecdc").c4b());
    _field->setColorSpaceHolder(Col("#a8a0b0").c4b());
    _field->setCursorEnabled(true);
    if (auto fa = _field->getFontAtlas()) fa->setAliasTexParameters();
    Node::addChild(_field);
    _keys = EventListenerKeyboard::create();
    _keys->onKeyPressed = [this](EventKeyboard::KeyCode k, Event*) {
        if (!_focused) return;
        if (k == EventKeyboard::KeyCode::KEY_ENTER || k == EventKeyboard::KeyCode::KEY_KP_ENTER)
        {
            text_submitted.emit(text());
            release_focus();
        }
    };
    _eventDispatcher->addEventListenerWithSceneGraphPriority(_keys, this);
    schedule([this](float) {
        std::string t = text();
        if (max_length > 0 && utf8_len(t) > (size_t)max_length)
        {
            t = t.substr(0, utf8_prefix(t, max_length));
            _field->setString(t);
        }
        if (t != (std::string)meta.value("_last", std::string()))
        {
            meta["_last"] = t;
            text_changed.emit(t);
        }
    }, 0.0f, "le_poll");
    return true;
}
std::string LineEdit::text() const { return std::string(_field->getString()); }
void LineEdit::set_text(const std::string& t) { _field->setString(t); meta["_last"] = t; }
void LineEdit::set_placeholder(const std::string& p) { _field->setPlaceHolder(p); }
void LineEdit::grab_focus() { _focused = _field->attachWithIME(); }
void LineEdit::release_focus() { _focused = false; _field->detachWithIME(); }
float LineEdit::content_min_h(float) { return gd::text_size(" ", font_size).y + _style.ch(); }
void LineEdit::on_gui_event(InputEvent& e)
{
    if (e.type == Ev::RELEASE) grab_focus();
    e.accept();
}
void LineEdit::onExit()
{
    release_focus();
    Control::onExit();
}
void LineEdit::size_changed()
{
    _bg->setContentSize(_size);
    float h = gd::text_size(" ", font_size).y;
    _field->setPosition(_style.content_margin[0], std::floor((_size.y - h) / 2));
}

// ================================================================== easing
float ease_value(float t, Trans tr, Ease e)
{
    auto in = [tr](float x) -> float {
        const float PI = 3.14159265f;
        switch (tr)
        {
        case TRANS_LINEAR: return x;
        case TRANS_SINE: return 1 - std::cos(x * PI / 2);
        case TRANS_QUAD: return x * x;
        case TRANS_CUBIC: return x * x * x;
        case TRANS_QUART: return x * x * x * x;
        case TRANS_QUINT: return x * x * x * x * x;
        case TRANS_EXPO: return x <= 0 ? 0 : std::pow(2.0f, 10 * (x - 1));
        case TRANS_CIRC: return 1 - std::sqrt(std::max(0.0f, 1 - x * x));
        case TRANS_BACK: { const float s = 1.70158f; return x * x * ((s + 1) * x - s); }
        case TRANS_ELASTIC:
            if (x <= 0 || x >= 1) return x;
            return -std::pow(2.0f, 10 * (x - 1)) * std::sin((x - 1.075f) * (2 * PI) / 0.3f);
        case TRANS_BOUNCE:
        {
            float y = 1 - x;   // bounce-out mirrored
            float o;
            if (y < 1 / 2.75f) o = 7.5625f * y * y;
            else if (y < 2 / 2.75f) { y -= 1.5f / 2.75f; o = 7.5625f * y * y + 0.75f; }
            else if (y < 2.5f / 2.75f) { y -= 2.25f / 2.75f; o = 7.5625f * y * y + 0.9375f; }
            else { y -= 2.625f / 2.75f; o = 7.5625f * y * y + 0.984375f; }
            return 1 - o;
        }
        }
        return x;
    };
    if (tr == TRANS_LINEAR) return t;
    switch (e)
    {
    case EASE_IN: return in(t);
    case EASE_OUT: return 1 - in(1 - t);
    case EASE_IN_OUT: return t < 0.5f ? in(t * 2) / 2 : 1 - in((1 - t) * 2) / 2;
    case EASE_OUT_IN: return t < 0.5f ? (1 - in(1 - t * 2)) / 2 : 0.5f + in(t * 2 - 1) / 2;
    }
    return t;
}

// ================================================================== Tween
struct Tween::Step
{
    float dur = 0;
    std::function<void()> start;
    std::function<void(float)> update;   // eased 0..1
    Trans trans = TRANS_LINEAR;
    Ease ease = EASE_IN_OUT;
};

class StepAction : public ActionInterval
{
public:
    std::shared_ptr<Tween::Step> step;
    static StepAction* make(std::shared_ptr<Tween::Step> s)
    {
        auto a = new StepAction();
        a->step = std::move(s);
        a->initWithDuration(std::max(0.0f, a->step->dur));
        a->autorelease();
        return a;
    }
    StepAction* clone() const override { return make(step); }
    StepAction* reverse() const override { return clone(); }
    void startWithTarget(Node* t) override
    {
        ActionInterval::startWithTarget(t);
        if (step->start) step->start();
    }
    void update(float t) override
    {
        if (step->update) step->update(ease_value(std::clamp(t, 0.0f, 1.0f), step->trans, step->ease));
    }
};

Tween::Tween(Node* owner) : _owner(owner)
{
    if (_owner) _owner->retain();
}
Tween::~Tween()
{
    if (!_started && _owner) _owner->release();
    if (_action) _action->release();
}

TweenRef tween(Node* owner)
{
    auto t = std::make_shared<Tween>(owner);
    std::weak_ptr<Tween> w = t;
    auto keep = t;   // lives until it starts
    Director::getInstance()->getScheduler()->runOnAxmolThread([keep] { keep->start(); });
    return t;
}

void Tween::add(std::shared_ptr<Step> s)
{
    s->trans = _default_trans;
    bool par = (_parallel_all || _next_parallel) && !_groups.empty() && !_force_new_group;
    if (par) _groups.back().push_back(s);
    else _groups.push_back({s});
    _next_parallel = false;
    _force_new_group = false;
}

Tween& Tween::trans(Trans t)
{
    if (!_groups.empty()) _groups.back().back()->trans = t;
    return *this;
}
Tween& Tween::ease(Ease e)
{
    if (!_groups.empty()) _groups.back().back()->ease = e;
    return *this;
}
Tween& Tween::loops(int n) { _loops = n; return *this; }

Tween& Tween::prop(std::function<float()> get, std::function<void(float)> set, float to, float dur)
{
    auto s = std::make_shared<Step>();
    auto from = std::make_shared<float>(0);
    s->dur = dur;
    s->start = [get, from] { *from = get(); };
    s->update = [set, from, to](float k) { set(*from + (to - *from) * k); };
    add(s);
    return *this;
}
Tween& Tween::prop2(std::function<Vec2()> get, std::function<void(Vec2)> set, Vec2 to, float dur)
{
    auto s = std::make_shared<Step>();
    auto from = std::make_shared<Vec2>();
    s->dur = dur;
    s->start = [get, from] { *from = get(); };
    s->update = [set, from, to](float k) { set(*from + (to - *from) * k); };
    add(s);
    return *this;
}
Tween& Tween::method(std::function<void(float)> f, float from, float to, float dur)
{
    auto s = std::make_shared<Step>();
    s->dur = dur;
    s->update = [f, from, to](float k) { f(from + (to - from) * k); };
    add(s);
    return *this;
}
Tween& Tween::alpha(Control* c, float to, float dur)
{
    return prop([c] { return c->alpha(); }, [c](float v) { c->set_alpha(v); }, to, dur);
}
Tween& Tween::modulate(Control* c, const Col& to, float dur)
{
    auto s = std::make_shared<Step>();
    auto from = std::make_shared<Col>();
    s->dur = dur;
    s->start = [c, from] { *from = c->modulate(); };
    s->update = [c, from, to](float k) { c->set_modulate(from->lerp(to, k)); };
    add(s);
    return *this;
}
Tween& Tween::position(Control* c, const Vec2& to, float dur)
{
    return prop2([c] { return c->position(); }, [c](Vec2 v) { c->set_position(v); }, to, dur);
}
Tween& Tween::position_x(Control* c, float to, float dur)
{
    return prop([c] { return c->position().x; }, [c](float v) { c->set_position_x(v); }, to, dur);
}
Tween& Tween::position_y(Control* c, float to, float dur)
{
    return prop([c] { return c->position().y; }, [c](float v) { c->set_position_y(v); }, to, dur);
}
Tween& Tween::shift(Control* c, const Vec2& to, float dur)
{
    return prop2([c] { return c->shift(); }, [c](Vec2 v) { c->set_shift(v); }, to, dur);
}
Tween& Tween::scale(Node* n, const Vec2& to, float dur)
{
    return prop2([n] { return Vec2(n->getScaleX(), n->getScaleY()); }, [n](Vec2 v) { n->setScale(v.x, v.y); }, to, dur);
}
Tween& Tween::rotation(Node* n, float deg, float dur)
{
    return prop([n] { return n->getRotation(); }, [n](float v) { n->setRotation(v); }, deg, dur);
}
Tween& Tween::node_pos(Node* n, const Vec2& to, float dur)
{
    return prop2([n] { return p2(n->getPosition()); }, [n](Vec2 v) { n->setPosition(p2(v)); }, to, dur);
}
Tween& Tween::opacity(Node* n, float to, float dur)
{
    return prop([n] { return n->getOpacity() / 255.0f; }, [n](float v) { n->setOpacity(u8(v)); }, to, dur);
}
Tween& Tween::interval(float dur)
{
    auto s = std::make_shared<Step>();
    s->dur = dur;
    add(s);
    return *this;
}
Tween& Tween::callback(std::function<void()> f)
{
    auto s = std::make_shared<Step>();
    s->dur = 0;
    s->start = std::move(f);
    add(s);
    return *this;
}

void Tween::start()
{
    if (_started) return;
    _started = true;
    Node* owner = _owner;
    if (_killed || !owner || !owner->isRunning() || _groups.empty())
    {
        if (!_killed && owner && owner->isRunning() && _finished) _finished();
        if (owner) owner->release();
        return;
    }
    Vector<FiniteTimeAction*> seq;
    for (auto& g : _groups)
    {
        if (g.size() == 1) seq.pushBack(StepAction::make(g[0]));
        else
        {
            Vector<FiniteTimeAction*> par;
            for (auto& s : g) par.pushBack(StepAction::make(s));
            seq.pushBack(Spawn::create(par));
        }
    }
    FiniteTimeAction* body = seq.size() == 1 ? seq.at(0) : (FiniteTimeAction*)Sequence::create(seq);
    Action* act;
    if (_loops == 0) act = RepeatForever::create((ActionInterval*)body);
    else
    {
        auto fin = _finished;
        act = Sequence::create(_loops == 1 ? body : (FiniteTimeAction*)Repeat::create(body, _loops),
                               CallFunc::create([fin] { if (fin) fin(); }), nullptr);
    }
    _action = act;
    _action->retain();   // kept so kill() stays safe after the tween finished or its owner died
    owner->runAction(act);
    owner->release();
}

void Tween::kill()
{
    _killed = true;
    if (_action)
    {
        Director::getInstance()->getActionManager()->removeAction(_action);   // no-op when already finished
        _action->release();
        _action = nullptr;
    }
}

// ================================================================== Particles
Particles* Particles::create(const ParticleCfg& cfg)
{
    GD_CREATE(Particles)
    c->_cfg = cfg;
    auto ps = ParticleSystemQuad::createWithTotalParticles(std::max(1, cfg.amount));
    Texture2D* tex = cfg.texture.empty() ? white_texture() : texture(cfg.texture);
    ps->setTexture(tex ? tex : white_texture());
    ps->setEmitterMode(ParticleSystem::Mode::GRAVITY);
    ps->setLife(cfg.lifetime);
    ps->setLifeVar(0);
    float rate = cfg.amount / std::max(0.01f, cfg.lifetime);
    if (cfg.explosiveness > 0.5f) rate = cfg.amount / 0.02f;
    ps->setEmissionRate(rate);
    ps->setDuration(cfg.one_shot ? std::max(0.02f, (cfg.explosiveness > 0.5f ? 0.02f : cfg.lifetime)) : (float)ParticleSystem::DURATION_INFINITY);
    Vec2 var = cfg.emission_rect;
    if (cfg.emission_radius > 0) var = Vec2(cfg.emission_radius, cfg.emission_radius);
    ps->setPosVar(var);
    ps->setGravity(Vec2(cfg.gravity.x, -cfg.gravity.y));
    float ang = std::atan2(-cfg.direction.y, cfg.direction.x) * 180.0f / 3.14159265f;
    ps->setAngle(ang);
    ps->setAngleVar(cfg.spread);
    ps->setSpeed((cfg.vel_min + cfg.vel_max) / 2);
    ps->setSpeedVar((cfg.vel_max - cfg.vel_min) / 2);
    float px = tex ? tex->getContentSize().x : 4;
    float size = (cfg.scale_min + cfg.scale_max) / 2 * (cfg.texture.empty() ? 1 : px);
    float size_var = (cfg.scale_max - cfg.scale_min) / 2 * (cfg.texture.empty() ? 1 : px);
    ps->setStartSize(size);
    ps->setStartSizeVar(size_var);
    ps->setEndSize(cfg.scale_end < 0 ? (float)ParticleSystem::START_SIZE_EQUAL_TO_END_SIZE : size * cfg.scale_end);
    Col a = cfg.ramp.empty() ? cfg.color : cfg.ramp.front(), b = cfg.ramp.empty() ? cfg.color : cfg.ramp.back();
    ps->setStartColor(a.c4f());
    ps->setStartColorVar(Color4F(0, 0, 0, 0));
    ps->setEndColor(b.c4f());
    ps->setEndColorVar(Color4F(0, 0, 0, 0));
    ps->setBlendAdditive(cfg.additive);
    ps->setPositionType(cfg.local_coords ? ParticleSystem::PositionType::GROUPED : ParticleSystem::PositionType::FREE);
    ps->setAutoRemoveOnFinish(false);
    ps->setPosition(Vec2::ZERO);
    c->_ps = ps;
    c->addChild(ps);
    if (cfg.preprocess > 0) ps->simulate(cfg.preprocess, 30);
    return c;
}
bool Particles::emitting() const { return _ps && _ps->isActive(); }
void Particles::set_emitting(bool on)
{
    if (!_ps) return;
    if (on) _ps->resetSystem();
    else _ps->stopSystem();
}
void Particles::restart() { if (_ps) _ps->resetSystem(); }

// ================================================================== AnimatedSprite
AnimatedSprite* AnimatedSprite::create()
{
    auto s = new AnimatedSprite();
    if (s->init())
    {
        s->autorelease();
        s->scheduleUpdate();
        return s;
    }
    delete s;
    return nullptr;
}
AnimatedSprite::~AnimatedSprite()
{
    for (auto& [k, a] : _anims)
        for (auto f : a.frames) f->release();
}
void AnimatedSprite::add_animation(const std::string& name, const std::vector<ax::Rect>& regions, Texture2D* tex, float fps, bool loop)
{
    SpriteAnim a;
    a.fps = fps;
    a.loop = loop;
    for (auto& r : regions)
    {
        auto f = SpriteFrame::createWithTexture(tex, r);
        f->retain();
        a.frames.push_back(f);
    }
    auto old = _anims.find(name);
    if (old != _anims.end())
        for (auto f : old->second.frames) f->release();
    _anims[name] = a;
}
int AnimatedSprite::frame_count(const std::string& name) const
{
    auto it = _anims.find(name);
    return it == _anims.end() ? 0 : (int)it->second.frames.size();
}
void AnimatedSprite::play(const std::string& name)
{
    if (!_anims.count(name)) return;
    if (name != _current || !_playing)
    {
        _current = name;
        _frame = 0;
        _t = 0;
    }
    _playing = true;
    set_frame(_frame);
}
void AnimatedSprite::stop() { _playing = false; }
void AnimatedSprite::set_frame(int f)
{
    auto it = _anims.find(_current);
    if (it == _anims.end() || it->second.frames.empty()) return;
    _frame = std::clamp(f, 0, (int)it->second.frames.size() - 1);
    bool fx = isFlippedX();
    setSpriteFrame(it->second.frames[_frame]);
    setFlippedX(fx);
    frame_changed.emit();
}
void AnimatedSprite::update(float dt)
{
    if (!_playing) return;
    auto it = _anims.find(_current);
    if (it == _anims.end() || it->second.frames.empty()) return;
    auto& a = it->second;
    _t += dt * speed_scale;
    float per = 1.0f / std::max(0.01f, a.fps);
    while (_t >= per && _playing)
    {
        _t -= per;
        int n = (int)a.frames.size();
        if (_frame + 1 >= n)
        {
            if (a.loop) set_frame(0);
            else
            {
                _playing = false;
                retain();
                animation_finished.emit();
                release();
                return;
            }
        }
        else
            set_frame(_frame + 1);
    }
}

// ================================================================== Root & input
Root* Root::get() { return g_root; }
Root* Root::create()
{
    GD_CREATE(Root)
    g_root = c;
    return c;
}
bool Root::init()
{
    if (!Control::init()) return false;
    mouse_filter = MOUSE_IGNORE;
    auto vs = Director::getInstance()->getVisibleSize();
    auto vo = Director::getInstance()->getVisibleOrigin();
    _size = Vec2(vs.width, vs.height);
    setContentSize(_size);
    setPosition(vo);
    auto touch = EventListenerTouchOneByOne::create();
    touch->setSwallowTouches(true);
    touch->onTouchBegan = [this](Touch* t, Event*) {
        if (_pressing) return false;
        press(to_gd(t->getLocation()));
        return true;
    };
    touch->onTouchMoved = [this](Touch* t, Event*) { move(to_gd(t->getLocation())); };
    touch->onTouchEnded = [this](Touch* t, Event*) { release(to_gd(t->getLocation()), false); };
    touch->onTouchCancelled = [this](Touch* t, Event*) { release(to_gd(t->getLocation()), true); };
    _eventDispatcher->addEventListenerWithSceneGraphPriority(touch, this);
    auto mouse = EventListenerMouse::create();
    mouse->onMouseMove = [this](EventMouse* e) {
        _mouse = to_gd(e->getLocation());
        if (_pressing || input_blocked) return true;
        Control* h = hit_test(_mouse);
        if (h != _hover.get())
        {
            ax::RefPtr<Control> old = _hover;
            _hover = h;
            if (old)
            {
                old->on_hover(false);
                old->mouse_exited.emit();
            }
            if (h)
            {
                h->on_hover(true);
                h->mouse_entered.emit();
            }
        }
        return true;
    };
    mouse->onMouseScroll = [this](EventMouse* e) {
        if (input_blocked) return true;
        _mouse = to_gd(e->getLocation());
        for (Control* c = hit_test(_mouse); c; c = c->parent_control())
            if (auto s = dynamic_cast<ScrollContainer*>(c))
            {
                InputEvent ev;
                ev.type = Ev::WHEEL;
                ev.global = _mouse;
                ev.local = s->to_local(_mouse);
                ev.wheel = e->getScrollY() < 0 ? 1.0f : -1.0f;
                s->on_gui_event(ev);
                if (s->can_scroll()) break;
            }
        return true;
    };
    _eventDispatcher->addEventListenerWithSceneGraphPriority(mouse, this);
    auto keys = EventListenerKeyboard::create();
    keys->onKeyPressed = [this](EventKeyboard::KeyCode k, Event*) { key_pressed.emit((int)k); };
    keys->onKeyReleased = [this](EventKeyboard::KeyCode k, Event*) { key_released.emit((int)k); };
    _eventDispatcher->addEventListenerWithSceneGraphPriority(keys, this);
    scheduleUpdate();
    return true;
}

Vec2 Root::to_gd(const Vec2& gl) const
{
    auto vo = Director::getInstance()->getVisibleOrigin();
    return Vec2(gl.x - vo.x, _size.y - (gl.y - vo.y));
}

void Root::layout_now()
{
    g_dirty = false;
    layout_children();
}

void Root::update(float)
{
    auto vs = Director::getInstance()->getVisibleSize();
    if (Vec2(vs.width, vs.height) != _size)
    {
        _size = Vec2(vs.width, vs.height);
        setContentSize(_size);
        g_dirty = true;
    }
    if (g_dirty) layout_now();
    for (int pass = 0; pass < 4 && !g_deferred.empty(); ++pass)
    {
        auto list = std::move(g_deferred);
        g_deferred.clear();
        for (auto& f : list) f();
        if (g_dirty) layout_now();
    }
}

static bool draw_before(Control* a, Control* b)
{
    if (a->getLocalZOrder() != b->getLocalZOrder()) return a->getLocalZOrder() < b->getLocalZOrder();
    return a->seq() < b->seq();
}

Control* Root::hit(Control* c, const Vec2& g, const Vec2& origin)
{
    if (!c->isVisible()) return nullptr;
    Vec2 tl = origin + c->position() + c->shift();
    Rect2 r{tl, c->size()};
    bool inside = r.has_point(g);
    if (c->clip_contents() && !inside) return nullptr;
    auto kids = c->children();
    std::stable_sort(kids.begin(), kids.end(), draw_before);
    for (auto it = kids.rbegin(); it != kids.rend(); ++it)
        if (auto h = hit(*it, g, tl)) return h;
    if (inside && c->mouse_filter != MOUSE_IGNORE) return c;
    return nullptr;
}

Control* Root::hit_test(const Vec2& g) { return hit(this, g, -_pos - _shift); }

void Root::dispatch(Control* target, InputEvent& e)
{
    for (Control* c = target; c; c = c->parent_control())
    {
        if (c->mouse_filter == MOUSE_IGNORE) continue;
        e.local = c->to_local(e.global);
        ax::RefPtr<Control> keep(c);
        c->on_gui_event(e);
        if (!e.accepted) c->gui_input.emit(e);
        if (e.accepted || c->mouse_filter == MOUSE_STOP) return;
    }
}

void Root::press(const Vec2& g)
{
    if (input_blocked) return;
    _pressing = true;
    _scroll_taken = false;
    _press_at = g;
    Control* t = hit_test(g);
    _capture = t;
    if (!t) return;
    InputEvent e;
    e.type = Ev::PRESS;
    e.global = g;
    dispatch(t, e);
}

void Root::move(const Vec2& g)
{
    _mouse = g;
    if (!_capture || !_capture->getParent()) return;
    if (!_scroll_taken && (g - _press_at).length() > 18)
    {
        // hand the gesture to the nearest scroll area that can move
        for (Control* c = _capture.get(); c; c = c->parent_control())
            if (auto s = dynamic_cast<ScrollContainer*>(c))
            {
                if (!s->can_scroll()) continue;
                if (s != _capture.get())
                {
                    InputEvent cancel;
                    cancel.type = Ev::CANCEL;
                    cancel.global = g;
                    dispatch(_capture.get(), cancel);
                }
                _capture = s;
                s->begin_drag(_press_at);
                _scroll_taken = true;
                break;
            }
    }
    InputEvent e;
    e.type = Ev::MOVE;
    e.global = g;
    dispatch(_capture.get(), e);
}

void Root::release(const Vec2& g, bool cancel)
{
    _pressing = false;
    ax::RefPtr<Control> c = _capture;
    _capture = nullptr;
    if (!c || !c->getParent()) return;
    InputEvent e;
    e.type = cancel ? Ev::CANCEL : Ev::RELEASE;
    e.global = g;
    dispatch(c.get(), e);
}

}  // namespace gd
