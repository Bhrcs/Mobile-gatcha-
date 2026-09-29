// Unit components: UnitCard, UnitFilter, SkillText, StatRow, StatusIcon, ItemSources
// (scripts/ui/components/unit_card.gd, unit_filter.gd, skill_text.gd, stat_row.gd,
// status_icon.gd, item_sources.gd).
#include "screens/Screens.h"

using namespace UIKit;
using gd::Rect2;

static std::string first_word(const std::string& s) { return s.substr(0, s.find(' ')); }
static std::string lower(std::string s) { for (auto& c : s) c = (char)tolower(c); return s; }
// String.get_slice(delim, i)
static std::string slice(const std::string& s, const std::string& d, int i)
{
    size_t start = 0;
    for (; i > 0; --i)
    {
        size_t p = s.find(d, start);
        if (p == std::string::npos) return "";
        start = p + d.size();
    }
    size_t e = s.find(d, start);
    return s.substr(start, e == std::string::npos ? std::string::npos : e - start);
}

// ============================================================ UnitCard
static constexpr int CARD_W = 244, CARD_H = 330;

UnitCard* UnitCard::make(const Json& u)
{
    auto c = gd::make<UnitCard>();
    c->unit = u;
    c->set_name("UnitTile_" + S(u, "uid"));
    c->set_custom_min(Vec2(CARD_W, CARD_H));
    const Json& def = DB.character(S(u, "char_id"));
    int rarity = I(def, "rarity", 3);
    auto frame = PanelFrame::make("rarity_" + std::to_string(std::clamp(rarity, 3, 6)), 12);
    frame->set_anchors_preset(gd::PRESET_FULL_RECT);
    frame->set_mouse_filter(gd::MOUSE_IGNORE);
    c->add(frame);
    auto v = vbox(2);
    v->set_mouse_filter(gd::MOUSE_IGNORE);
    frame->add(v);
    v->add(portrait_art(def, Vec2(CARD_W - 24, 208)));
    v->add(label(first_word(S(def, "name")), 30, TEXT, gd::ALIGN_CENTER, 6));
    auto row = hbox(4);
    row->alignment = gd::ALIGNMENT_CENTER;
    row->add(orb(S(def, "element"), 32));
    row->add(role_icon(def, 32));
    int lvl = I(u, "level", 1), max_l = I(def, "max_level", 20);
    row->add(label(lvl >= max_l ? "Lv.MAX" : UIKit::fmt("Lv.%d", lvl), 30, GOLD, gd::ALIGN_LEFT, 6));
    v->add(row);
    // Fixed indicator positions (the same on every card):
    //   top-left: squad / leader    top-right: NEW > EVOLVE > MAX
    //   art bottom-left: lock, favourite    art bottom-right: rarity stars
    auto st = stars(rarity, 16);
    st->set_position(Vec2(CARD_W - 20 - rarity * 16, 190));
    c->add(st);
    std::string uid = S(u, "uid");
    if (GM.is_in_party(uid))
    {
        bool leader = S(at(GM.party_uids(), 0)) == uid;
        auto tl = hbox(2);
        tl->set_name("SquadMark");
        tl->set_position(Vec2(14, 14));
        tl->set_mouse_filter(gd::MOUSE_IGNORE);
        if (leader) tl->add(icon("assets/icons/leader.png", 32));
        tl->add(tag(leader ? "LEADER" : "SQUAD", leader ? Col("#b8281e") : Col("#2a5a9a")));
        c->add(tl);
    }
    auto flags = hbox(2);
    flags->set_name("Flags");
    flags->set_position(Vec2(14, 172));
    flags->set_mouse_filter(gd::MOUSE_IGNORE);
    if (B(u, "locked", false)) flags->add(icon("assets/icons/lock.png", 32));
    if (B(u, "favorite", false)) flags->add(icon("assets/icons/fav.png", 32));
    c->add(flags);
    std::string status;
    Col col("#c8281e");
    if (B(u, "new", false))
        status = "NEW";
    else if (GM.feature_unlocked("evolution") && GM.can_evolve(uid))
        status = "EVOLVE", col = Col("#8a5a10");
    else if (lvl >= max_l)
        status = "MAX", col = Col("#3a3a4a");
    if (!status.empty())
    {
        auto t = tag(status, col);
        t->set_name(status == "NEW" ? "NewTag" : "StatusTag");
        c->add(t);
        Vec2 m = t->combined_min();
        t->set_size(m);
        t->set_position(Vec2(CARD_W - 14 - m.x, 14));
    }
    if (rarity >= 5) sparkle(c, Rect2{Vec2(12, 12), Vec2(CARD_W - 24, 200)});
    on_tap(c, [c, uid] { c->tapped.emit(uid); });
    return c;
}

gd::TextureRect* UnitCard::role_icon(const Json& def, int size)
{
    std::string role = lower(S(def, "role", S(def, "class", "attacker")));
    std::string path = "assets/icons/role_" + role + ".png";
    auto ic = icon(gd::exists(path) ? path : "assets/icons/role_attacker.png", size);
    ic->tooltip_text = capitalize(role);
    return ic;
}

void UnitCard::set_selected(bool on)
{
    selected = on;
    set_modulate(on ? Col(1.15f, 1.1f, 0.95f) : Col::WHITE);   // clamps to (1, 1, 0.95)
}

// ============================================================ UnitFilter
namespace UnitFilter
{
static const std::vector<std::pair<std::string, std::string>> SORTS = {
    {"RECENT", "recent"}, {"LEVEL", "level"}, {"RARITY", "rarity"}, {"POWER", "power"}, {"HP", "hp"},
    {"ATK", "atk"}, {"DEF", "def"}, {"REC", "rec"}, {"NAME", "name"}, {"ELEMENT", "element"}};
static const Json DEFAULT = {{"el", "all"}, {"rarity", 0}, {"role", ""}, {"evolve", false}, {"fav", false}};

Json load_state()
{
    Json st = DEFAULT;
    std::string raw = S(GM.settings, "unit_filter", "");
    if (!raw.empty())
    {
        Json parsed = Json::parse(raw, nullptr, false);
        if (parsed.is_object())
            for (auto& [k, v] : DEFAULT.items())
                if (parsed.contains(k)) st[k] = parsed[k];
    }
    st["el"] = S(st, "el", "all");
    st["role"] = S(st, "role", "");
    st["rarity"] = I(st, "rarity", 0);
    st["evolve"] = B(st, "evolve", false);
    st["fav"] = B(st, "fav", false);
    st["sort"] = S(GM.settings, "unit_sort", "recent");
    st["desc"] = B(GM.settings, "unit_sort_desc", true);
    return st;
}

void save_state(const Json& st)
{
    Json f = Json::object();
    for (auto& [k, v] : DEFAULT.items()) f[k] = st.contains(k) ? st[k] : v;
    GM.set_setting("unit_filter", f.dump());
    GM.set_setting("unit_sort", S(st, "sort", "recent"));
    GM.set_setting("unit_sort_desc", B(st, "desc", true));
}

int active_count(const Json& st)
{
    int n = 0;
    for (auto& [k, v] : DEFAULT.items())
        if (at(st, k) != v) n++;
    return n;
}

std::string sort_label(const Json& st)
{
    for (auto& s : SORTS)
        if (s.second == S(st, "sort", "recent")) return s.first + " " + (B(st, "desc", true) ? "v" : "^");
    return "SORT";
}

bool matches(const Json& st, const Json& u, const Json& def)
{
    std::string el = S(st, "el", "all"), role = S(st, "role");
    if (el != "all" && S(def, "element") != el) return false;
    if (I(st, "rarity", 0) > 0 && I(def, "rarity", 3) != I(st, "rarity", 0)) return false;
    if (!role.empty() && lower(S(def, "role")) != role) return false;
    if (B(st, "fav", false) && !B(u, "favorite", false)) return false;
    if (B(st, "evolve", false) && !GM.can_evolve(S(u, "uid"))) return false;
    return true;
}

// sort key: names compare as text, everything else as a number
static std::pair<long long, std::string> key(const std::string& sort, const Json& e)
{
    const Json &u = at(e, "unit"), &def = at(e, "def");
    if (sort == "level") return {I(u, "level", 1), ""};
    if (sort == "rarity") return {I(def, "rarity", 3) * 1000LL + I(u, "level", 1), ""};
    if (sort == "power") return {GM.unit_power(u), ""};
    if (sort == "hp" || sort == "atk" || sort == "def" || sort == "rec") return {I(at(e, "stats"), sort, 0), ""};
    if (sort == "name") return {0, S(def, "name")};
    if (sort == "element")
    {
        static const std::vector<std::string> order = {"nature", "water", "fire"};
        auto it = std::find(order.begin(), order.end(), S(def, "element"));
        return {it == order.end() ? -1 : it - order.begin(), ""};
    }
    return {I(e, "idx", 0), ""};
}

// Comparison on entries {unit, def, idx, stats}.
bool compare(const Json& st, const Json& a, const Json& b)
{
    std::string sort = S(st, "sort", "recent");
    bool desc = B(st, "desc", true);
    auto ka = key(sort, a), kb = key(sort, b);
    if (ka == kb) return I(a, "idx", 0) > I(b, "idx", 0);
    bool less = ka < kb;
    // names read A-Z by default; everything else biggest first by default
    if (sort == "name") return desc ? less : !less;
    return desc ? !less : less;
}

struct Ctx
{
    Json st;
    gd::BoxContainer* body;
    std::function<void(Json)> on_apply;
};
using CtxP = std::shared_ptr<Ctx>;
static void fill(const CtxP& ctx);

static void pick(const CtxP& ctx, const std::string& k, const Json& value)
{
    ctx->st[k] = value;
    save_state(ctx->st);
    ctx->on_apply(ctx->st);
    gd::after(ctx->body, 0.0f, [ctx] { fill(ctx); });   // call_deferred: the pressed button lives in body
}

static std::string str(const Json& v) { return v.is_string() ? v.get<std::string>() : std::to_string(I(v)); }

static std::string label_of(const std::string& k, const Json& v)
{
    if (k == "el") return S(v) == "all" ? "ALL" : upper(DB.element_name(S(v)));
    if (k == "rarity") return I(v) == 0 ? "ALL" : UIKit::fmt("%d STAR", I(v));
    if (k == "role") return S(v).empty() ? "ALL" : upper(S(v));
    if (k == "sort")
        for (auto& s : SORTS)
            if (s.second == S(v)) return s.first;
    return str(v);
}

static gd::Label* section(const std::string& text) { return label(text, T_SMALL, GOLD, gd::ALIGN_LEFT, 5); }

static gd::GridContainer* choices(const CtxP& ctx, const std::string& k, const Json& values, const std::string& prefix, int cols = 4)
{
    auto g = gd::GridContainer::create((int)values.size() > cols ? cols : (int)values.size());
    g->h_separation = SP_S;
    g->v_separation = SP_S;
    for (auto& v : values)
    {
        bool on = v == at(ctx->st, k);
        std::string text = label_of(k, v);
        auto b = btn(text, on ? "reward" : "quiet", Vec2(900.0f / g->columns - SP_S, 84));
        b->set_name(prefix + str(v));
        b->set_h_flags(gd::SIZE_EXPAND_FILL);
        b->set_font_size(text.size() < 9 ? T_BODY : T_SMALL);
        b->pressed.connect([ctx, k, v] { pick(ctx, k, v); });
        g->add(b);
    }
    return g;
}

static void fill(const CtxP& ctx)
{
    const Json& st = ctx->st;
    auto body = ctx->body;
    body->clear_children();
    body->add(section("ELEMENT"));
    body->add(choices(ctx, "el", {"all", "fire", "water", "nature"}, "Filter_el_"));
    body->add(section("RARITY"));
    body->add(choices(ctx, "rarity", {0, 3, 4, 5}, "Filter_rarity_"));
    body->add(section("ROLE"));
    body->add(choices(ctx, "role", {"", "attacker", "defender", "healer", "support", "breaker"}, "Filter_role_", 3));
    auto toggles = hbox(SP_L);
    for (auto t : {std::pair<const char*, const char*>{"CAN EVOLVE", "evolve"}, {"FAVORITES", "fav"}})
    {
        std::string k = t.second;
        bool on = B(st, k, false);
        auto b = btn(t.first, on ? "reward" : "quiet", Vec2(0, 92));
        b->set_name("Filter_" + k);
        b->set_h_flags(gd::SIZE_EXPAND_FILL);
        b->pressed.connect([ctx, k, on] { pick(ctx, k, !on); });
        toggles->add(b);
    }
    body->add(toggles);
    body->add(separator());
    auto sh = hbox(SP_M);
    auto sl = section("SORT BY");
    sl->set_h_flags(gd::SIZE_EXPAND_FILL);
    sh->add(sl);
    bool desc = B(st, "desc", true);
    std::string dir_text = S(st, "sort") != "name" ? (desc ? "HIGH FIRST" : "LOW FIRST") : (desc ? "A - Z" : "Z - A");
    auto dir = btn(dir_text, "secondary", Vec2(300, 88));
    dir->set_name("SortDirection");
    dir->pressed.connect([ctx, desc] { pick(ctx, "desc", !desc); });
    sh->add(dir);
    body->add(sh);
    Json keys = Json::array();
    for (auto& s : SORTS) keys.push_back(s.second);
    body->add(choices(ctx, "sort", keys, "Sort_", 5));
}

FantasyPopup* open(gd::Control* parent, const Json& st, std::function<void(Json)> on_apply)
{
    auto p = FantasyPopup::open(parent, "FILTER & SORT", 980);
    p->set_name("FilterPopup");
    p->tap_outside_closes = true;
    auto body = vbox(SP_M);
    p->content->add(body);
    auto ctx = std::make_shared<Ctx>(Ctx{st, body, std::move(on_apply)});
    fill(ctx);
    auto row = hbox(SP_XL);
    row->alignment = gd::ALIGNMENT_CENTER;
    auto reset = btn("RESET", "quiet", Vec2(300, 110));
    reset->set_name("FilterReset");
    reset->pressed.connect([ctx] {
        for (auto& [k, v] : DEFAULT.items()) ctx->st[k] = v;
        ctx->st["sort"] = "recent";
        ctx->st["desc"] = true;
        save_state(ctx->st);
        ctx->on_apply(ctx->st);
        fill(ctx);
    });
    auto done = btn("DONE", "primary", Vec2(300, 110));
    done->set_name("FilterDone");
    done->pressed.connect([p] { p->close(); });
    row->add(reset);
    row->add(done);
    p->content->add(row);
    p->default_action = [p] { p->close(); };
    return p;
}
}  // namespace UnitFilter

// ============================================================ SkillText
namespace SkillText
{
// Colour is unused by chips() (they tint with the accent); kept for the declared signature.
std::vector<std::pair<std::string, Col>> tags(const Json& sk)
{
    std::vector<std::string> out;
    auto add_once = [&out](const std::string& t) {
        if (std::find(out.begin(), out.end(), t) == out.end()) out.push_back(t);
    };
    static const Json targets = {{"enemy_single", "1 FOE"}, {"enemy_all", "ALL FOES"}, {"ally_all", "ALL ALLIES"},
                                 {"ally_single", "1 ALLY"}, {"self", "SELF"}};
    std::string target = S(sk, "target");
    out.push_back(S(targets, target, upper(target)));
    double power = F(sk, "power", 0.0);
    if (power > 0.0) out.push_back(UIKit::fmt("%d%% ATK", (int)std::round(power * 100.0)));
    if (I(sk, "hits", 0) > 1) out.push_back(UIKit::fmt("%d HITS", I(sk, "hits", 0)));
    for (auto& eff : A(sk, "effects"))
    {
        std::string type = S(eff, "type");
        if (type == "heal" || type == "cleanse" || type == "shield")
            add_once(upper(type));
        else if (type == "status")
        {
            std::string sid = S(eff, "status");
            std::string t = upper(S(DB.status(sid), "name", sid));
            double ch = F(eff, "chance", 1.0);
            if (ch < 1.0) t += UIKit::fmt(" %d%%", (int)std::round(ch * 100.0));
            add_once(t);
        }
    }
    std::vector<std::pair<std::string, Col>> res;
    for (auto& t : out) res.push_back({t, TEXT});
    return res;
}

gd::FlowContainer* chips(const Json& sk, const Col& accent)
{
    auto row = gd::FlowContainer::create();
    row->set_name("SkillTags");
    row->h_separation = SP_S;
    row->v_separation = SP_S;
    row->set_mouse_filter(gd::MOUSE_IGNORE);
    for (auto& t : tags(sk)) row->add(tag(t.first, accent.darkened(0.55f)));
    return row;
}
}  // namespace SkillText

// ============================================================ StatRow
StatRow* StatRow::make(const std::string& stat_name, int value, int ref_max, const Col& color)
{
    auto r = gd::make<StatRow>();
    r->vertical = false;
    r->separation = 14;
    auto n = label(stat_name, 30, color, gd::ALIGN_LEFT, 6);
    n->set_min_w(90);
    r->add(n);
    auto bar = ResourceBar::make("stat", 30);
    bar->set_h_flags(gd::SIZE_EXPAND_FILL);
    bar->set_v_flags(gd::SIZE_SHRINK_CENTER);
    r->add(bar);
    bar->set_values((float)value, (float)std::max(ref_max, 1), false);
    auto v = label(std::to_string(value), 40, TEXT, gd::ALIGN_RIGHT, 6);
    v->set_min_w(120);
    r->add(v);
    return r;
}

// ============================================================ StatusIcon
StatusIcon* StatusIcon::make(const std::string& sid, int t, float v, int px)
{
    auto s = gd::make<StatusIcon>();
    s->status_id = sid;
    s->turns = t;
    s->value = v;
    s->set_custom_min(Vec2(px, px));
    s->set_mouse_filter(gd::MOUSE_STOP);
    const Json& sdef = DB.status(sid);
    s->add(icon(S(sdef, "icon"), px));
    if (t > 0 && sid != "charging")
    {
        auto l = label(std::to_string(t), 20, Col::WHITE, gd::ALIGN_RIGHT, 6);
        l->set_position(Vec2(px - 22, px - 26));
        l->set_size(Vec2(24, 26));
        s->add(l);
    }
    UIManager::attach_tooltip(s, S(sdef, "name", sid), slice(s->describe(), " - ", 1), S(sdef, "icon"));
    // keep taps on the icon from also targeting the enemy underneath
    s->gui_input.connect([](gd::InputEvent& e) {
        if (e.type == gd::Ev::PRESS || e.type == gd::Ev::RELEASE) e.accept();
    });
    return s;
}

// "Burn - loses 5% max HP each turn (2 turns left)"
std::string StatusIcon::describe() const
{
    const Json& sdef = DB.status(status_id);
    std::string kind = S(sdef, "kind"), effect;
    if (kind == "dot")
        effect = UIKit::fmt("loses %d%% max HP each turn", (int)(F(sdef, "dot_percent_max_hp", 0.05) * 100));
    else if (kind == "stat_mod")
        effect = UIKit::fmt("%s %s%d%%", upper(S(sdef, "stat")).c_str(), I(sdef, "sign", 1) < 0 ? "-" : "+", (int)std::round(value * 100));
    else if (kind == "hot")
        effect = UIKit::fmt("recovers %d%% max HP each turn", (int)std::round(value * 100));
    else if (kind == "shield")
        effect = UIKit::fmt("absorbs %d more damage", (int)value);
    else if (kind == "charge")
        effect = "unleashes a powerful attack on its next action - Guard!";
    else if (kind == "damage_reduction")
        effect = UIKit::fmt("takes %d%% less damage", (int)std::round(value * 100));
    else if (kind == "taunt")
        effect = "draws enemy attacks";
    std::string name = S(sdef, "name", status_id);
    if (turns <= 0 || status_id == "charging") return name + " - " + effect;
    return UIKit::fmt("%s - %s (%d turn%s left)", name.c_str(), effect.c_str(), turns, turns == 1 ? "" : "s");
}

// ============================================================ ItemSources
namespace ItemSources
{
static void go(gd::Control* parent, const std::string& kind, const std::string& sid)
{
    if (kind == "stage") SceneRouter::go("stage_select", {{"highlight", sid}});
    else if (kind == "tower") SceneRouter::go("tower", {{"highlight", sid}});
    else if (kind == "missions") SceneRouter::go("missions");
    else toast(parent, "Log in each day to collect login rewards.", GOLD);
}

FantasyPopup* open(gd::Control* parent, const std::string& item_id)
{
    const Json& item = DB.item(item_id);
    auto p = FantasyPopup::open(parent, "WHERE TO FIND", 960);
    p->set_name("ItemSourcesPopup");
    auto head = hbox(14);
    head->alignment = gd::ALIGNMENT_CENTER;
    head->add(icon(S(item, "icon"), 80));
    auto hv = vbox(2);
    hv->add(label(S(item, "name", item_id), T_NAME, TEXT, gd::ALIGN_LEFT, 8));
    hv->add(label(UIKit::fmt("Owned: %d", GM.item_count(item_id)), T_SMALL, GOLD, gd::ALIGN_LEFT, 5));
    head->add(hv);
    p->content->add(head);
    auto use = wrap_label(S(item, "use"), T_SMALL, MUTED);
    use->set_min_w(880);
    use->set_align(gd::ALIGN_CENTER);
    p->content->add(use);
    auto scroll = gd::ScrollContainer::create();
    scroll->set_custom_min(Vec2(900, 620));
    p->content->add(scroll);
    auto list = vbox(8);
    list->set_h_flags(gd::SIZE_EXPAND_FILL);
    scroll->add(list);
    Json sources = GM.item_sources(item_id);
    if (sources.empty()) list->add(label("No known source yet.", T_BODY, MUTED, gd::ALIGN_CENTER));
    for (size_t i = 0; i < sources.size() && i < 16; i++)
    {
        const Json& src = sources[i];
        bool unlocked = B(src, "unlocked", false);
        std::string kind = S(src, "kind"), sid = S(src, "id");
        auto row = PanelFrame::make(unlocked ? "plank" : "inset", 8);
        row->set_name("Src_" + sid);
        auto h = hbox(10);
        row->add(h);
        std::string icon_path = kind == "tower" ? "assets/icons/tower.png"
                                : kind == "missions" ? "assets/icons/missions.png"
                                : kind == "login" ? "assets/icons/login.png" : "assets/icons/world.png";
        h->add(icon(icon_path, 48));
        auto v = vbox(0);
        v->set_h_flags(gd::SIZE_EXPAND_FILL);
        v->add(label(S(src, "label"), T_BODY, unlocked ? TEXT : MUTED, gd::ALIGN_LEFT, 6));
        if (kind == "stage" || kind == "tower") v->add(label(S(DB.stage(sid), "name"), T_SMALL, MUTED, gd::ALIGN_LEFT, 4));
        h->add(v);
        if (unlocked)
        {
            auto g = FantasyButton::make("GO", "ember", Vec2(150, 80));
            g->set_font_size(30);
            g->pressed.connect([p, parent, kind, sid] {
                p->close();
                go(parent, kind, sid);
            });
            h->add(g);
        }
        else
        {
            h->add(icon("assets/icons/lock.png", 40));
            h->add(label("LOCKED", T_SMALL, MUTED, gd::ALIGN_LEFT, 4));
        }
        list->add(row);
    }
    auto close = FantasyButton::make("CLOSE", "stone", Vec2(280, 100));
    close->set_h_flags(gd::SIZE_SHRINK_CENTER);
    close->pressed.connect([p] { p->close(); });
    p->content->add(close);
    return p;
}
}  // namespace ItemSources
