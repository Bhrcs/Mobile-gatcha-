// Elemental Towers (scripts/ui/tower.gd): three climbs of ten floors each. Floors unlock one by
// one; the docked sheet shows the selected floor and START -> PREPARE.
#include "screens/Screens.h"

using namespace gd;

namespace
{
constexpr int SHEET_H = 660;
Col tower_color(const std::string& el, const Col& fallback)
{
    if (el == "fire") return Col("#ff8a4a");
    if (el == "water") return Col("#5ac8ff");
    if (el == "nature") return Col("#8ae05a");
    return fallback;
}
}  // namespace

class Tower : public ScreenBase
{
public:
    std::string tower_id;
    Json tower = Json::object();
    BoxContainer* list = nullptr;
    ScrollContainer* scroll = nullptr;
    BoxContainer* sheet_body = nullptr;
    PanelFrame* sheet = nullptr;
    std::string selected_id;
    std::map<std::string, Control*> rows;

    void ready() override
    {
        if (!require_profile()) return;
        std::string hl = S(params(), "highlight");
        tower_id = S(params(), "tower", hl.empty() ? "" : S(DB.stage(hl), "world_id"));
        if (!DB.towers.contains(tower_id)) tower_id = DB.tower_order[0];
        tower = DB.towers[tower_id];
        auto area = build_frame("bg_tower", "ELEMENTAL TOWERS", "tower", nullptr, 0.45f, true, {{"help", "tower"}});
        if (!GM.feature_unlocked("tower"))
        {
            auto lock = UIKit::wrap_label("The Towers open after clearing " + GM.feature_unlock_label("tower") + ".", UIKit::T_NAME, UIKit::MUTED);
            lock->set_align(ALIGN_CENTER);
            lock->set_min_w(900);
            lock->set_anchors_preset(PRESET_CENTER);
            area->add(lock);
            return;
        }
        auto col = UIKit::vbox(10);
        col->set_anchors_preset(PRESET_FULL_RECT);
        col->set_offset(SIDE_BOTTOM, -SHEET_H - 10);
        area->add(col);

        auto tabs = UIKit::hbox(10);
        tabs->set_name("TowerTabs");
        for (auto& tid : DB.tower_order)
        {
            const Json& td = at(DB.towers, tid);
            std::string el = S(td, "element", "fire");
            std::string name = S(td, "name");
            auto b = FantasyButton::make(upper(name.substr(0, name.find(' '))), tid == tower_id ? "gold" : "steel", Vec2(0, 100),
                                         "assets/icons/orb_" + el + ".png");
            b->set_name("Tower_" + tid);
            b->set_h_flags(SIZE_EXPAND_FILL);
            b->set_font_size(32);
            if (tid != tower_id) b->pressed.connect([tid] { SceneRouter::go("tower", {{"tower", tid}}); });
            tabs->add(b);
        }
        col->add(tabs);

        auto head = PanelFrame::make("plank", 12);
        auto hv = UIKit::vbox(4);
        head->add(hv);
        std::string el = S(tower, "element", "fire");
        auto r1 = UIKit::hbox(12);
        r1->add(UIKit::orb(el, 56));
        auto nm = UIKit::label(upper(S(tower, "name")), UIKit::T_NAME, tower_color(el, UIKit::TEXT), ALIGN_LEFT, 8);
        nm->set_h_flags(SIZE_EXPAND_FILL);
        r1->add(nm);
        r1->add(UIKit::label(UIKit::fmt("BEST FLOOR %d / %d", GM.tower_highest_floor(tower_id), int(A(tower, "stages").size())),
                             UIKit::T_BODY, UIKit::GOLD, ALIGN_RIGHT, 6));
        hv->add(r1);
        auto r2 = UIKit::hbox(10);
        std::string counter = S(tower, "counter_element");
        r2->add(UIKit::label("Bring", UIKit::T_SMALL, UIKit::MUTED, ALIGN_LEFT, 5));
        r2->add(UIKit::orb(counter, 32));
        r2->add(UIKit::label(DB.element_name(counter) + " heroes.  Materials:", UIKit::T_SMALL, UIKit::MUTED, ALIGN_LEFT, 5));
        for (auto& m : A(tower, "materials")) r2->add(UIKit::icon(S(DB.item(S(m)), "icon"), 40));
        hv->add(r2);
        col->add(head);

        scroll = ScrollContainer::create();
        scroll->set_v_flags(SIZE_EXPAND_FILL);
        col->add(scroll);
        list = UIKit::vbox(0);
        list->set_h_flags(SIZE_EXPAND_FILL);
        scroll->add(list);
        Json floors = A(tower, "stages");
        std::reverse(floors.begin(), floors.end());   // climb upwards: top floor first
        for (size_t i = 0; i < floors.size(); ++i)
        {
            const Json& fl = floors[i];
            // the stair between this floor and the one above, lit once that floor is open
            if (i > 0) list->add(connector(GM.is_stage_unlocked(S(floors[i - 1], "id"))));
            rows[S(fl, "id")] = list->add(floor_row(fl));
        }

        sheet = PanelFrame::make("panel", 24);
        sheet->set_name("FloorSheet");
        sheet->set_anchors_preset(PRESET_BOTTOM_WIDE);
        sheet->set_offset(SIDE_TOP, -SHEET_H);
        area->add(sheet);
        sheet_body = UIKit::vbox(10);
        sheet->add(sheet_body);
        std::string start = hl;
        if (start.empty() || S(DB.stage(start), "world_id") != tower_id) start = next_floor();
        select(start);
        AudioManager::play_music(S(tower, "music", "tower"));
        if (B(params(), "prepare", false) && GM.is_stage_unlocked(start)) StageInfo::open_prepare(this, start, "tower");
    }

    std::string next_floor()
    {
        const Json& floors = A(tower, "stages");
        std::string best = S(at(floors, 0), "id");
        for (auto& fl : floors)
            if (GM.is_stage_unlocked(S(fl, "id"))) best = S(fl, "id");
        return best;
    }

    // Vertical stair segment in the tower's own path style (ember / tide / verdant).
    Control* connector(bool lit)
    {
        auto c = Control::create();
        c->set_custom_min(Vec2(0, 34));
        c->set_mouse_filter(MOUSE_IGNORE);
        std::string el = S(tower, "element", "fire");
        std::string tname = el == "water" ? "tide" : el == "nature" ? "verdant" : "ember";
        auto path = TextureRect::create(UIKit::UI_DIR + "p5_path_" + tname + ".png");
        path->stretch = STRETCH_TILE;
        path->ignore_size = true;
        path->set_size(Vec2(12, 16));
        path->setScale(3);   // 1x pixel art shown at 3x
        path->set_position(Vec2(40, -7));
        path->set_modulate(lit ? Col::WHITE : Col(0.35f, 0.33f, 0.4f));
        path->set_mouse_filter(MOUSE_IGNORE);
        c->add(path);
        return c;
    }

    Control* floor_row(const Json& fl)
    {
        std::string sid = S(fl, "id");
        bool unlocked = GM.is_stage_unlocked(sid);
        bool cleared = GM.is_stage_cleared(sid);
        bool boss = B(fl, "boss", false);
        auto p = PanelFrame::make(boss && unlocked ? "boss" : (unlocked ? "plank" : "inset"), 10);
        p->set_name(UIKit::fmt("Floor_%d", I(fl, "number", 0)));
        auto h = UIKit::hbox(14);
        h->set_mouse_filter(MOUSE_IGNORE);
        p->add(h);
        auto badge = PanelFrame::make("slot", 4);
        if (unlocked)
        {
            // self_modulate: tint only the badge frame
            StyleBox sb = badge->style();
            sb.modulate = tower_color(S(tower, "element", "fire"), Col::WHITE).lightened(0.3f);
            badge->set_style(sb);
        }
        badge->set_custom_min(Vec2(96, 76));
        badge->add(UIKit::label(std::to_string(I(fl, "number", 0)), UIKit::T_NAME, unlocked ? UIKit::GOLD : UIKit::MUTED, ALIGN_CENTER, 8));
        h->add(badge);
        auto v = UIKit::vbox(0);
        v->set_h_flags(SIZE_EXPAND_FILL);
        v->set_mouse_filter(MOUSE_IGNORE);
        v->add(UIKit::label(S(fl, "name"), UIKit::T_BODY, unlocked ? Col("#fff0c0") : UIKit::MUTED, ALIGN_LEFT, 6));
        auto sub = UIKit::hbox(10);
        sub->add(UIKit::icon("assets/icons/energy.png", 28));
        sub->add(UIKit::label(std::to_string(I(fl, "energy", 0)), UIKit::T_SMALL, Col("#ffe07a"), ALIGN_LEFT, 5));
        sub->add(UIKit::label("POWER " + UIKit::format_number(I(fl, "recommended_power", 0)), UIKit::T_SMALL, UIKit::MUTED, ALIGN_LEFT, 5));
        if (boss) sub->add(UIKit::tag("GUARDIAN", Col("#7a1a14")));
        v->add(sub);
        h->add(v);
        if (cleared)
        {
            Json got = GM.stage_stars(sid);
            for (int i = 0; i < 3; ++i)
                h->add(UIKit::icon(B(at(got, (size_t)i)) ? "assets/icons/star.png" : "assets/icons/star_empty.png", 32));
        }
        else if (!unlocked)
            h->add(UIKit::icon("assets/icons/lock.png", 48));
        else
            h->add(UIKit::tag("NEXT", Col("#b8401e")));
        UIKit::on_tap(p, [this, sid] { select(sid); });
        return p;
    }

    void select(const std::string& sid)
    {
        selected_id = sid;
        for (auto& [id, r] : rows) r->set_modulate(id == sid ? Col(1.15f, 1.1f, 0.95f) : Col::WHITE);
        AudioManager::play_sfx("stage_select", 0.03f, -4.0f);
        auto it = rows.find(sid);
        if (it != rows.end()) scroll_to(it->second);
        sheet_body->clear_children();
        const Json& st = DB.stage(sid);
        bool unlocked = GM.is_stage_unlocked(sid);
        sheet->set_variant(B(st, "boss", false) ? "boss" : "panel", 24);
        auto head = UIKit::hbox(12);
        std::string fname = S(st, "name");
        std::string title = fname.rfind("Floor", 0) == 0 ? GM.stage_label(sid) : GM.stage_label(sid) + "  -  " + fname;
        auto t = UIKit::label(title, UIKit::T_NAME, Col("#fff0c0"), ALIGN_LEFT, 8);
        t->set_name("FloorTitle");
        t->set_h_flags(SIZE_EXPAND_FILL);
        t->set_clip_text(true);
        head->add(t);
        sheet_body->add(head);
        if (!unlocked)
        {
            auto l = UIKit::label("Clear the floor below to climb higher.", UIKit::T_BODY, UIKit::MUTED, ALIGN_CENTER);
            l->set_v_flags(SIZE_EXPAND_FILL);
            sheet_body->add(l);
        }
        else
        {
            sheet_body->add(StageInfo::info_row(st));
            sheet_body->add(StageInfo::stars_row(st));
            sheet_body->add(StageInfo::rewards_row(st));
        }
        sheet_body->add(UIKit::spacer(false, true));
        auto go = FantasyButton::make("START", "ember", Vec2(600, 116));
        go->set_name("StartButton");
        go->set_h_flags(SIZE_SHRINK_CENTER);
        go->set_font_size(UIKit::T_HEAD);
        go->set_disabled(!unlocked);
        go->pressed.connect([this, sid] { StageInfo::open_prepare(this, sid, "tower"); });
        sheet_body->add(go);
    }

    void scroll_to(Control* n)
    {
        ax::RefPtr<Tower> self(this);
        gd::defer([self, n] {
            if (self->is_inside_tree())
                self->scroll->set_scroll_vertical(n->position().y - self->scroll->size().y / 2 + n->size().y / 2);
        });
    }
};
REGISTER_SCREEN("tower", Tower)
