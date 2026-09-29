// Adventure map (scripts/ui/stage_select.gd): a portrait route per world with LOCKED / AVAILABLE /
// CLEARED / BOSS nodes and earned stars. The docked sheet shows energy, power, star objectives,
// possible drops and first-clear rewards; START opens the PREPARE check.
#include "screens/Screens.h"
#include <cmath>

using namespace gd;

class StageSelect : public ScreenBase
{
public:
    static constexpr float MAP_SCALE = 4.0f;
    static constexpr int NODE_PX = 96, BOSS_PX = 128, SHEET_H = 700;

    Json world = Json::object();
    std::map<std::string, StageNode*> nodes;
    ScrollContainer* map_scroll = nullptr;
    Control* map_view = nullptr;
    ax::DrawNode* path_draw = nullptr;
    PanelFrame* sheet = nullptr;
    BoxContainer* sheet_body = nullptr;
    std::string selected_id;
    TextureRect* marker = nullptr;
    TweenRef marker_tw;
    float dash = 0;

    void ready() override
    {
        if (!require_profile()) return;
        std::string start = S(params(), "highlight", GM.last_unlocked_stage);
        if (start.empty() || !GM.is_stage_unlocked(start) || DB.is_tower_stage(start)) start = latest_unlocked();
        std::string wid = S(params(), "world", S(DB.stage(start), "world_id"));
        if (!DB.worlds.contains(wid)) wid = DB.world_order[0];
        world = DB.worlds[wid];
        if (S(DB.stage(start), "world_id") != wid) start = latest_unlocked_in(wid);
        back_fallback = "world_select";
        auto area = build_frame("bg_camp", upper(S(world, "name", "Quest")), "world_select", nullptr, 0.6f);

        // ---- map (scrolls vertically)
        auto frame = PanelFrame::make("inset", 6);
        frame->set_anchors_preset(PRESET_FULL_RECT);
        frame->set_offset(SIDE_TOP, 0);
        frame->set_offset(SIDE_BOTTOM, -SHEET_H - 10);
        area->add(frame);
        map_scroll = ScrollContainer::create();
        map_scroll->show_bar = false;
        frame->add(map_scroll);
        auto center = CenterContainer::create();
        center->set_h_flags(SIZE_EXPAND_FILL);
        map_scroll->add(center);
        map_view = Control::create();
        map_view->set_mouse_filter(MOUSE_PASS);   // touch-drag scrolls the map (ScrollContainer drag)
        auto tex = gd::texture(res(S(world, "route_map", "assets/environments/bg_routemap.png")));
        Vec2 msize = (tex ? Vec2(tex->getContentSize()) : Vec2(256, 448)) * MAP_SCALE;
        map_view->set_custom_min(msize);
        center->add(map_view);
        auto map_tex = UIKit::tex_rect(tex, msize);
        map_tex->set_size(msize);
        map_view->add(map_tex);
        add_ambient();
        auto path_layer = Node2D::create();
        path_layer->set_mouse_filter(MOUSE_IGNORE);
        path_draw = ax::DrawNode::create();
        path_layer->addChild(path_draw);
        map_view->add(path_layer);
        build_nodes();

        // ---- docked stage sheet
        sheet = PanelFrame::make("panel", 26);
        sheet->set_name("StageSheet");
        sheet->set_anchors_preset(PRESET_BOTTOM_WIDE);
        sheet->set_offset(SIDE_TOP, -SHEET_H);
        area->add(sheet);
        sheet_body = UIKit::vbox(12);
        sheet->add(sheet_body);

        select(start, false);
        AudioManager::play_music(S(world, "music", "world"));
        if (B(params(), "prepare", false) && GM.is_stage_unlocked(start))
            StageInfo::open_prepare(this, start);
        else if (GM.stages_cleared_count() == 0 && nodes.count(DB.stage_order[0]))
            UIManager::guide("select_first_stage", sheet->find("StartButton"), "Tap START to begin Stage 1-1.");
        scheduleUpdate();
    }

    void update(float dt) override
    {
        dash = std::fmod(dash + dt * 18.0f, 24.0f);
        draw_route();
    }

    std::string latest_unlocked()
    {
        std::string last = DB.stage_order[0];
        for (auto& sid : DB.stage_order)
            if (GM.is_stage_unlocked(sid)) last = sid;
        return last;
    }

    std::string latest_unlocked_in(const std::string& wid)
    {
        const Json& stages = A(DB.worlds[wid], "stages");
        std::string last = S(stages[0], "id");
        for (auto& st : stages)
            if (GM.is_stage_unlocked(S(st, "id"))) last = S(st, "id");
        return last;
    }

    // Node types, told apart by shape and icon (not colour alone):
    // locked (padlock), open (ember ring), elite (diamond), boss (large crest),
    // cleared (bronze ring + check), perfect (gold ring + check, all 3 stars).
    std::string node_state(const Json& stage)
    {
        std::string sid = S(stage, "id");
        if (!GM.is_stage_unlocked(sid)) return "locked";
        if (B(stage, "boss", false)) return "boss";
        if (GM.is_stage_cleared(sid)) return GM.star_count(sid) >= 3 ? "perfect" : "cleared";
        return DB.stage_has_elite(sid) ? "elite" : "open";
    }

    std::string node_tip(const Json& stage, const std::string& st)
    {
        if (st == "locked") return "Locked - clear the previous stage first.";
        if (st == "elite") return "Elite foes: tougher enemies with extra tricks.";
        if (st == "boss") return std::string("Ancient Foe: a boss battle.") + (GM.is_stage_cleared(S(stage, "id")) ? "  Defeated." : "");
        if (st == "perfect") return "Cleared with all 3 stars.";
        if (st == "cleared") return UIKit::fmt("Cleared - %d / 3 stars.", GM.star_count(S(stage, "id")));
        return UIKit::fmt("New stage - %d Energy.", I(stage, "energy", 0));
    }

    Vec2 route_point(const Json& stage)
    {
        const Json& p = at(stage, "route_pos");
        return (p.is_array() ? Vec2((float)F(at(p, 0)), (float)F(at(p, 1))) : Vec2(128, 224)) * MAP_SCALE;
    }

    void build_nodes()
    {
        for (auto& stage : A(world, "stages"))
        {
            std::string sid = S(stage, "id");
            std::string st = node_state(stage);
            bool boss = B(stage, "boss", false);
            int px = boss ? BOSS_PX : NODE_PX;
            float fpx = (float)px;
            auto n = StageNode::make(sid, boss ? "boss" : st, px);
            n->set_position(route_point(stage) - Vec2(fpx, fpx) / 2.0f - Vec2(0, 16));
            if (boss && st == "locked") n->set_modulate(Col(0.45f, 0.4f, 0.5f));
            if (boss && GM.is_stage_cleared(sid))
            {
                auto chk = UIKit::icon("assets/icons/check.png", 48);
                chk->set_position(Vec2(fpx - 44, fpx - 52));
                n->add(chk);
            }
            UIManager::attach_tooltip(n, GM.stage_label(sid) + "  " + (st != "locked" ? S(stage, "name") : "???"), node_tip(stage, st));
            n->gui_input.connect([this, n, sid](InputEvent& e) {   // TextureButton.pressed
                if (e.released() && Rect2{Vec2::ZERO, n->size()}.has_point(e.local)) select(sid);
            });
            map_view->add(n);
            nodes[sid] = n;
            auto num = UIKit::label(std::to_string(I(stage, "number", 0)), UIKit::T_BODY, st != "locked" ? UIKit::TEXT : UIKit::MUTED,
                                    ALIGN_CENTER, 8);
            num->set_position(n->position() + Vec2(0, fpx - 4));
            num->set_size(Vec2(fpx, 34));
            map_view->add(num);
            if (GM.is_stage_cleared(sid))
            {
                auto srow = UIKit::hbox(0);
                srow->set_name("Stars_" + sid);
                Json got = GM.stage_stars(sid);
                for (int i = 0; i < 3; ++i)
                    srow->add(UIKit::icon(B(at(got, (size_t)i)) ? "assets/icons/star.png" : "assets/icons/star_empty.png", 24));
                srow->set_position(n->position() + Vec2(fpx / 2.0f - 36, fpx + 26));
                map_view->add(srow);
            }
            if (boss)
            {
                auto tag = UIKit::tag("ANCIENT FOE", Col("#7a1a14"));
                tag->set_position(n->position() + Vec2(fpx / 2.0f - 110, -44));
                map_view->add(tag);
            }
        }
        marker = TextureRect::create(UIKit::UI_DIR + "v2_chevron.png");
        marker->ignore_size = true;
        marker->set_size(Vec2(64, 64));
        marker->set_mouse_filter(MOUSE_IGNORE);
        map_view->add(marker);
    }

    // Trail dots: lit and marching up to the furthest unlocked stage, dark beyond it.
    void draw_route()
    {
        path_draw->clear();
        const Json& stages = A(world, "stages");
        for (size_t i = 0; i + 1 < stages.size(); ++i)
        {
            Vec2 a = route_point(stages[i]), b = route_point(stages[i + 1]);
            bool reached = GM.is_stage_unlocked(S(stages[i + 1], "id"));
            float dist = a.distance(b);
            float d = 60.0f + (reached ? dash : 0.0f);
            Col lit = reached ? Col("#ffd88a") : Col(0.22f, 0.18f, 0.14f);
            while (d < dist - 50.0f)
            {
                Vec2 p = a.lerp(b, d / dist);
                path_draw->drawSolidRect(p2(p - Vec2(8, 8)), p2(p + Vec2(8, 8)), Col(0.06f, 0.04f, 0.03f, 0.85f).c4f());
                path_draw->drawSolidRect(p2(p - Vec2(4, 4)), p2(p + Vec2(4, 4)), lit.c4f());
                d += 24.0f;
            }
        }
    }

    // Drifting light motes and falling leaves over the map.
    void add_ambient()
    {
        Vec2 size = map_view->custom_min();
        ParticleCfg l;
        l.amount = 18;
        l.lifetime = 7.0f;
        l.preprocess = 7.0f;
        l.emission_rect = Vec2(size.x / 2, 10);
        l.direction = Vec2(0.3f, 1);
        l.gravity = Vec2(10, 40);
        l.vel_min = 40;
        l.vel_max = 90;
        l.scale_min = 6;
        l.scale_max = 8;
        l.color = S(world, "id") == "ashroot_wilds" ? Col("#8ac04a") : Col("#bff4ff");   // lifetime_randomness not supported
        auto leaves = Particles::create(l);
        leaves->set_position(Vec2(size.x / 2, -20));
        map_view->add(leaves);

        ParticleCfg g;
        g.amount = 14;
        g.lifetime = 3.0f;
        g.preprocess = 3.0f;
        g.emission_radius = 90;
        g.gravity = Vec2(0, -12);
        g.vel_max = 8;
        g.scale_min = 4;
        g.scale_max = 8;
        g.ramp = {Col("#c8ff9a"), Col(0.5f, 1.0f, 0.4f, 0.0f)};
        auto glow = Particles::create(g);
        const Json& stages = A(world, "stages");
        Vec2 heart = stages.empty() ? Vec2(512, 200) : route_point(stages.back());
        glow->set_position(heart + Vec2(0, -80));
        map_view->add(glow);

        ParticleCfg e;   // scorched band
        e.amount = 12;
        e.lifetime = 2.5f;
        e.preprocess = 2.5f;
        e.emission_rect = Vec2(size.x / 2, 20 * MAP_SCALE);
        e.gravity = Vec2(0, -30);
        e.vel_max = 12;
        e.scale_min = 4;
        e.scale_max = 6;
        e.ramp = {Col("#ffb04a"), Col(1, 0.3f, 0.1f, 0)};
        auto embers = Particles::create(e);
        embers->set_position(Vec2(size.x / 2, 200 * MAP_SCALE));
        map_view->add(embers);
    }

    void select(const std::string& sid, bool with_sound = true)
    {
        selected_id = sid;
        for (auto& [id, n] : nodes) n->set_selected(id == sid);
        if (with_sound) AudioManager::play_sfx("stage_select", 0.03f, -2.0f);
        auto it = nodes.find(sid);
        if (it != nodes.end())
        {
            StageNode* n = it->second;
            float y = n->position().y - 76;
            marker->set_position(Vec2(n->position().x + n->size().x / 2 - 32, y));
            if (marker_tw) marker_tw->kill();
            marker_tw = gd::tween(this);
            marker_tw->loops();
            marker_tw->position_y(marker, y - 14, 0.4f).trans(TRANS_SINE);
            marker_tw->position_y(marker, y, 0.4f).trans(TRANS_SINE);
            scroll_to(n);
        }
        build_sheet(sid);
    }

    void scroll_to(Control* n)
    {
        ax::RefPtr<StageSelect> self(this);
        gd::defer([self, n] {
            if (!self->is_inside_tree()) return;
            auto s = self->map_scroll;
            float target = std::round(n->position().y + n->size().y / 2 - s->size().y / 2);
            target = std::clamp(target, 0.0f, self->map_view->custom_min().y);
            gd::tween(self.get())->prop([s] { return s->scroll_vertical(); }, [s](float v) { s->set_scroll_vertical(v); }, target, 0.25f);
        });
    }

    void build_sheet(const std::string& sid)
    {
        sheet_body->clear_children();
        const Json& stage = DB.stage(sid);
        bool unlocked = GM.is_stage_unlocked(sid);
        bool cleared = GM.is_stage_cleared(sid);
        bool boss = B(stage, "boss", false);
        sheet->set_variant(boss ? "boss" : "panel", 26);

        auto head = UIKit::hbox(16);
        auto badge = PanelFrame::make("slot", 8);
        badge->set_custom_min(Vec2(110, 90));
        badge->add(UIKit::label(std::to_string(I(stage, "number", 0)), UIKit::T_HEAD, UIKit::GOLD, ALIGN_CENTER, 8));
        head->add(badge);
        auto tv = UIKit::vbox(2);
        tv->set_h_flags(SIZE_EXPAND_FILL);
        auto title = UIKit::label(unlocked ? S(stage, "name") : "? ? ?", UIKit::T_HEAD, unlocked ? Col("#fff0c0") : UIKit::MUTED, ALIGN_LEFT, 10);
        title->set_name("StageTitle");
        tv->add(title);
        bool elite = !boss && DB.stage_has_elite(sid);
        std::string sub = boss ? "ANCIENT FOE AWAITS" : (cleared ? "CLEARED" : (unlocked ? (elite ? "ELITE FOES" : "NEW") : "LOCKED"));
        tv->add(UIKit::label(sub, UIKit::T_BODY,
                             boss ? Col("#ff7a5a") : (cleared ? UIKit::GOOD : (unlocked ? UIKit::EMBER : UIKit::MUTED)), ALIGN_LEFT, 6));
        head->add(tv);
        sheet_body->add(head);

        if (!unlocked)
        {
            std::string prev;
            for (auto& [_, st2] : DB.stages.items())
                if (contains(A(st2, "unlocks"), Json(sid))) prev = GM.stage_label(S(st2, "id"));
            auto lock = UIKit::hbox(14);
            lock->alignment = ALIGNMENT_CENTER;
            lock->add(UIKit::icon("assets/icons/lock.png", 64));
            lock->add(UIKit::label("Clear " + prev + " to unlock this path.", UIKit::T_BODY, UIKit::MUTED));
            lock->set_v_flags(SIZE_EXPAND_FILL);
            sheet_body->add(lock);
        }
        else
        {
            sheet_body->add(StageInfo::info_row(stage));
            auto summary = UIKit::wrap_label(S(stage, "summary"), UIKit::T_SMALL, Col("#e0d6c6"));
            summary->set_min_w(980);
            sheet_body->add(summary);
            sheet_body->add(StageInfo::stars_row(stage));
            sheet_body->add(StageInfo::rewards_row(stage));
        }
        sheet_body->add(UIKit::spacer(false, true));
        auto go = FantasyButton::make("START", "ember", Vec2(640, 120));
        go->set_name("StartButton");
        go->set_h_flags(SIZE_SHRINK_CENTER);
        go->set_font_size(UIKit::T_HEAD);
        go->set_disabled(!unlocked);
        go->pressed.connect([this, sid] { start(sid); });
        go->add_shine();
        sheet_body->add(go);
        if (unlocked)
        {
            // over-bright pulse: modulate > 1 clamps in the toolkit, kept for parity
            auto tw = gd::tween(go);
            tw->loops();
            tw->modulate(go, Col(1.18f, 1.1f, 1.0f), 0.6f).trans(TRANS_SINE);
            tw->modulate(go, Col::WHITE, 0.6f).trans(TRANS_SINE);
        }
    }

    void start(const std::string& sid)
    {
        if (!GM.is_stage_unlocked(sid)) return;
        StageInfo::open_prepare(this, sid);
    }
};
REGISTER_SCREEN("stage_select", StageSelect)
