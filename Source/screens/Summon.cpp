// EMBERGATE summon hall (scripts/ui/summon.gd) + the summon ceremony (scripts/ui/components/summon_ceremony.gd).
#include "screens/Screens.h"

using namespace gd;

static Col rarity_color(int r)
{
    return r == 3 ? Col("#e0a060") : r == 4 ? Col("#d8e4f4") : r == 5 ? Col("#ffd84a") : Col::WHITE;
}

// ================================================================== SummonCeremony
// One hero at a time: fragments -> gate flare -> rarity light + stars -> silhouette -> reveal.
// Godot awaits become a small sequencer driven by update(): wait(t, next) / wait_tap(next).
class SummonCeremony : public Control
{
public:
    Signal<> finished;

    void play(const Json& results, bool can_skip)
    {
        _results = results;
        _can_skip = can_skip;
        build();
        scheduleUpdate();
        next_result();
    }

    void update(float dt) override
    {
        if (!_next) return;
        if (_tap_wait)
        {
            _waited += dt;
            if (!_tapped && !_skip && !(_results.size() > 1 && _waited > 1.6f)) return;
        }
        else
        {
            _left -= dt * (_tapped ? 4.0f : 1.0f);
            if (_left > 0 && !_skip) return;
        }
        auto f = std::move(_next);
        _next = nullptr;
        f();
    }

private:
    Json _results;
    size_t _index = 0;
    bool _can_skip = false, _skip = false, _tapped = false, _tap_wait = false;
    float _left = 0, _waited = 0;
    std::function<void()> _next;
    Control* _stage = nullptr;
    TextureRect* _vortex = nullptr;
    int _vframe = 0;
    Vec2 _center, _vp;

    void wait(float t, std::function<void()> f)
    {
        if (_skip) { f(); return; }
        _tap_wait = false;
        _left = t;
        _next = std::move(f);
    }

    void build()
    {
        set_anchors_and_offsets_preset(PRESET_FULL_RECT);
        set_mouse_filter(MOUSE_STOP);
        set_z(80);
        gui_input.connect([this](InputEvent& e) {
            if (e.pressed()) _tapped = true;
        });
        auto bg = ColorRect::create(Col(0.02f, 0.01f, 0.04f, 0.97f));
        bg->set_anchors_preset(PRESET_FULL_RECT);
        bg->set_mouse_filter(MOUSE_IGNORE);
        add(bg);
        _vp = Root::get()->size();
        _center = Vec2(_vp.x / 2, _vp.y * 0.44f);
        float k = 8;
        _vortex = TextureRect::create("assets/ui/embergate_vortex.png");
        _vortex->ignore_size = true;
        _vortex->set_region(ax::Rect(0, 0, 64, 64));
        _vortex->set_size(Vec2(56, 56) * k);
        _vortex->set_position(_center - _vortex->size() / 2 + Vec2(0, 20));
        _vortex->set_pivot(_vortex->size() / 2);
        _vortex->set_mouse_filter(MOUSE_IGNORE);
        add(_vortex);
        auto frame = UIKit::tex_rect(texture("assets/ui/embergate_frame.png"), Vec2(96, 128) * k);
        frame->set_size(frame->custom_min());
        frame->set_position(_center - Vec2(48, 60) * k);
        add(frame);
        schedule([this](float) {
            _vframe = (_vframe + 1) % 6;
            _vortex->set_region(ax::Rect(_vframe * 64.0f, 0, 64, 64));
        }, 0.1f, "vortex");
        _stage = Control::create();
        _stage->set_anchors_preset(PRESET_FULL_RECT);
        _stage->set_mouse_filter(MOUSE_IGNORE);
        add(_stage);
        if (_can_skip)
        {
            auto skip = FantasyButton::make("SKIP", "stone", Vec2(220, 96));
            skip->set_name("SkipSummon");
            skip->set_position(Vec2(_vp.x - 250, UIKit::safe_top() + 30));
            skip->set_z(5);
            skip->pressed.connect([this] {
                _skip = true;
                _tapped = true;
            });
            add(skip);
        }
        auto hint = UIKit::label("TAP TO CONTINUE", UIKit::T_SMALL, UIKit::MUTED, ALIGN_CENTER, 5);
        hint->set_position(Vec2(0, _vp.y - 120 - UIKit::safe_bottom()));
        hint->set_size(Vec2(_vp.x, 40));
        add(hint);
    }

    void next_result()
    {
        if (_skip || _index >= _results.size())
        {
            finished.emit();
            return;
        }
        reveal(_results[_index], (int)_index, (int)_results.size());
        ++_index;
    }

    void reveal(const Json& e, int index, int total)
    {
        _stage->clear_children();
        _tapped = false;
        const Json& d = DB.character(S(e, "char_id"));
        int rarity = I(e, "rarity", 3);
        Col rcol = rarity_color(rarity);
        if (total > 1)
        {
            auto cnt = UIKit::label(UIKit::fmt("%d / %d", index + 1, total), UIKit::T_BODY, UIKit::MUTED, ALIGN_LEFT, 5);
            cnt->set_position(Vec2(40, UIKit::safe_top() + 40));
            _stage->add(cnt);
        }
        // 1) fragments
        AudioManager::play_sfx("summon_charge", 0.03f);
        const Col cols[] = {Col("#ff8a3a"), Col("#5ac8ff"), Col("#8ae05a")};
        for (int i = 0; i < 18; ++i)
        {
            auto f = ColorRect::create(cols[i % 3].lightened(0.2f));
            f->set_size(Vec2(16, 16));
            float a = 2 * (float)M_PI * i / 18.0f;
            f->set_position(_center + Vec2(std::cos(a), std::sin(a)) * 520);
            f->set_mouse_filter(MOUSE_IGNORE);
            _stage->add(f);
            auto tw = tween(f);
            tw->interval(i * 0.012f);
            tw->position(f, _center - Vec2(8, 8), 0.55f).trans(TRANS_QUAD).ease(EASE_IN);
            tw->callback([f] { f->queue_free(); });
        }
        Json ej = e;
        wait(0.65f, [this, ej, d, rarity, rcol] {
            // 2) the gate flares in the rarity colour (over-bright modulate clamps to white)
            auto gtw = tween(this);
            gtw->modulate(_vortex, Col::WHITE, 0.15f);
            gtw->modulate(_vortex, rcol.lightened(0.3f) * Col(1.6f, 1.6f, 1.6f, 1), 0.3f);
            gtw->parallel().scale(_vortex, Vec2(1.15f, 1.15f), 0.3f);
            wait(0.45f, [this, ej, d, rarity, rcol] { rarity_light(ej, d, rarity, rcol); });
        });
    }

    // 3) rarity light + stars
    void rarity_light(const Json& e, const Json& d, int rarity, Col rcol)
    {
        auto glow = UIKit::tex_rect(texture(UIKit::fmt("assets/ui/rarity_glow_%d.png", std::clamp(rarity, 3, 5))),
                                    Vec2(32, 32) * (float)(14 + rarity * 2));
        glow->set_size(glow->custom_min());
        glow->set_position(_center - glow->size() / 2);
        glow->set_pivot(glow->size() / 2);
        glow->set_alpha(0);
        _stage->add(glow);
        auto gl = tween(glow);
        gl->set_parallel();
        gl->alpha(glow, 0.9f, 0.25f);
        gl->rotation(glow, 0.6f * 180.0f / (float)M_PI, 2.5f);
        if (rarity >= 5)
        {
            AudioManager::play_sfx("summon_rare");
            auto fl = ColorRect::create(Col(1.0f, 0.9f, 0.4f, 0.8f));
            fl->set_anchors_preset(PRESET_FULL_RECT);
            fl->set_mouse_filter(MOUSE_IGNORE);
            _stage->add(fl);
            tween(fl)->alpha(fl, 0.0f, 0.6f);
            UIKit::sparkle(_stage, Rect2{Vec2(_center.x - 400, _center.y - 500), Vec2(800, 900)}, Col("#ffe08a"), 40);
        }
        else if (rarity == 4)
            UIKit::sparkle(_stage, Rect2{Vec2(_center.x - 300, _center.y - 400), Vec2(600, 700)}, Col("#e8f0ff"), 20);
        auto stars = UIKit::hbox(6);
        stars->set_position(Vec2(_vp.x / 2 - rarity * 38, _center.y - 520));
        _stage->add(stars);
        star(stars, 0, e, d, rarity, rcol);
    }

    void star(BoxContainer* stars, int i, const Json& e, const Json& d, int rarity, Col rcol)
    {
        if (i >= rarity || _skip)
        {
            silhouette(e, d, rcol);
            return;
        }
        auto st = UIKit::icon("assets/icons/star.png", 72);
        stars->add(st);
        st->set_pivot(Vec2(36, 36));
        st->setScale(2);
        tween(st)->scale(st, Vec2(1, 1), 0.15f).trans(TRANS_BACK);
        AudioManager::play_sfx("reward", 0.05f, -8.0f);
        Json ej = e, dj = d;
        wait(0.14f, [this, stars, i, ej, dj, rarity, rcol] { star(stars, i + 1, ej, dj, rarity, rcol); });
    }

    // 4) silhouette
    void silhouette(const Json& e, const Json& d, Col rcol)
    {
        auto sp = UnitSpriteDisplay::make(O(d, "sprite"), 14.0f, false);
        sp->set_size(sp->custom_min());
        sp->set_position(Vec2(_center.x - sp->size().x / 2, _center.y + 330 - sp->size().y));
        sp->set_modulate(Col(0, 0, 0, 0));
        _stage->add(sp);
        tween(sp)->modulate(sp, Col(0, 0, 0, 1), 0.35f);
        Json ej = e, dj = d;
        wait(0.6f, [this, sp, ej, dj, rcol] { show_hero(sp, ej, dj, rcol); });
    }

    // 5) reveal
    void show_hero(UnitSpriteDisplay* sp, const Json& e, const Json& d, Col rcol)
    {
        AudioManager::play_sfx("summon_reveal");
        auto flash = ColorRect::create(Col(1, 1, 1, 0.95f));
        flash->set_anchors_preset(PRESET_FULL_RECT);
        flash->set_mouse_filter(MOUSE_IGNORE);
        _stage->add(flash);
        tween(flash)->alpha(flash, 0.0f, 0.4f);
        sp->set_modulate(Col::WHITE);
        sp->play("victory");
        auto nm = UIKit::label(S(d, "name"), UIKit::T_HEAD, rcol.lightened(0.2f), ALIGN_CENTER, 12);
        nm->set_name("RevealName");
        nm->set_position(Vec2(0, _center.y + 360));
        nm->set_size(Vec2(_vp.x, 70));
        _stage->add(nm);
        auto sub = UIKit::hbox(10);
        sub->alignment = ALIGNMENT_CENTER;
        sub->set_position(Vec2(0, _center.y + 440));
        sub->set_size(Vec2(_vp.x, 60));
        sub->add(UIKit::orb(S(d, "element"), 48));
        sub->add(UIKit::label(DB.element_name(S(d, "element")) + "  " + S(d, "role"), UIKit::T_BODY, UIKit::TEXT, ALIGN_LEFT, 6));
        _stage->add(sub);
        if (B(e, "is_new", false))
        {
            auto nt = UIKit::label("NEW!", 90, Col("#ff5a4a"), ALIGN_CENTER, 14);
            nt->set_name("NewStamp");
            nt->set_position(Vec2(_vp.x / 2 + 120, _center.y - 380));
            nt->set_size(Vec2(300, 100));
            nt->setRotation(0.2f * 180.0f / (float)M_PI);
            nt->set_pivot(Vec2(150, 50));
            nt->setScale(2.5f);
            _stage->add(nt);
            tween(nt)->scale(nt, Vec2(1, 1), 0.2f).trans(TRANS_BACK);
        }
        else
        {
            auto dup = UIKit::label(UIKit::fmt("Already owned  >  +%d Soul Shards", I(e, "shards", 0)), UIKit::T_BODY, Col("#d0a8ff"),
                                    ALIGN_CENTER, 6);
            dup->set_position(Vec2(0, _center.y + 510));
            dup->set_size(Vec2(_vp.x, 50));
            _stage->add(dup);
        }
        // wait for a tap (multi summons auto-advance)
        _tapped = false;
        _tap_wait = true;
        _waited = 0;
        _next = [this] {
            auto rt = tween(this);
            rt->modulate(_vortex, Col::WHITE, 0.2f);
            rt->parallel().scale(_vortex, Vec2(1, 1), 0.2f);
            next_result();
        };
        if (_skip) update(0);
    }
};

// ================================================================== Summon screen
class SummonScreen : public ScreenBase
{
public:
    static constexpr int GATE_SCALE = 6;
    Json banner;
    Label *gems_label = nullptr, *shards_label = nullptr;
    TextureRect* vortex = nullptr;
    int vortex_frame = 0;
    bool busy = false;

    void ready() override
    {
        if (!require_profile()) return;
        banner = GM.summon_banner("standard");
        auto area = build_frame("bg_title", "EMBERGATE", "summon", nullptr, 0.55f);
        if (!GM.feature_unlocked("summon"))
        {
            auto lock = UIKit::wrap_label("The Embergate awakens after clearing " + GM.feature_unlock_label("summon") + ".", UIKit::T_NAME,
                                          UIKit::MUTED);
            lock->h_align = ALIGN_CENTER;
            lock->set_anchors_preset(PRESET_CENTER);
            lock->set_min_w(900);
            area->add(lock);
            return;
        }
        GM.mark_summon_seen();
        auto col = UIKit::vbox(12);
        col->set_anchors_preset(PRESET_FULL_RECT);
        area->add(col);

        // banner
        auto bp = PanelFrame::make("panel", 10);
        bp->set_name("Banner");
        col->add(bp);
        auto bv = UIKit::vbox(6);
        bp->add(bv);
        auto art = UIKit::tex_rect(texture(res(S(banner, "art", "res://assets/ui/banner_standard.png"))), Vec2(900, 360));
        art->set_h_flags(SIZE_SHRINK_CENTER);
        bv->add(art);
        auto br = UIKit::hbox(10);
        auto bt = UIKit::vbox(0);
        bt->set_h_flags(SIZE_EXPAND_FILL);
        bt->add(UIKit::label(upper(S(banner, "name")), UIKit::T_NAME, UIKit::GOLD, ALIGN_LEFT, 8));
        auto desc = UIKit::wrap_label(S(banner, "description"), UIKit::T_SMALL, Col("#e0d6c6"));
        desc->set_min_w(640);
        bt->add(desc);
        Json rr = SummonSystem::rates(banner);
        bt->add(UIKit::label("5* " + pct(F(rr, "5", 0.0)) + "   4* " + pct(F(rr, "4", 0.0)) + "   3* " + pct(F(rr, "3", 0.0)), UIKit::T_SMALL,
                             UIKit::SKY, ALIGN_LEFT, 5));
        br->add(bt);
        auto details = FantasyButton::make("DETAILS", "steel", Vec2(230, 96));
        details->set_name("SummonDetails");
        details->set_font_size(30);
        details->pressed.connect([this] { open_details(); });
        br->add(details);
        bv->add(br);

        // gate
        auto gate = Control::create();
        gate->set_name("Gate");
        gate->set_custom_min(Vec2(0, 128 * GATE_SCALE * 0.62f));
        gate->set_v_flags(SIZE_EXPAND_FILL);
        gate->set_mouse_filter(MOUSE_IGNORE);
        col->add(gate);
        vortex = TextureRect::create("assets/ui/embergate_vortex.png");
        vortex->ignore_size = true;
        vortex->set_mouse_filter(MOUSE_IGNORE);
        vortex->set_region(ax::Rect(0, 0, 64, 64));
        gate->add(vortex);
        auto frame = UIKit::tex_rect(texture("assets/ui/embergate_frame.png"), Vec2(96, 128) * (GATE_SCALE * 0.62f));
        gate->add(frame);
        gate->resized.connect([this, gate, frame] {
            Vec2 fs = frame->size();
            frame->set_position(Vec2((gate->size().x - fs.x) / 2, (gate->size().y - fs.y) / 2));
            float k = fs.x / 96.0f;
            vortex->set_size(Vec2(56, 56) * k);
            vortex->set_position(frame->position() + Vec2(20, 34) * k);
        });
        schedule([this](float) {
            vortex_frame = (vortex_frame + 1) % 6;
            vortex->set_region(ax::Rect(vortex_frame * 64.0f, 0, 64, 64));
        }, 0.12f, "vortex");
        UIKit::sparkle(gate, Rect2{Vec2(200, 60), Vec2(650, 500)}, Col("#ffb04a"), 10);

        // currency + buttons
        auto cur = UIKit::hbox(24);
        cur->alignment = ALIGNMENT_CENTER;
        auto g = UIKit::hbox(8);
        g->add(UIKit::icon("assets/icons/gem.png", 48));
        gems_label = UIKit::label("", UIKit::T_NAME, Col("#9ae8ff"), ALIGN_LEFT, 8);
        gems_label->set_name("GemsOwned");
        g->add(gems_label);
        cur->add(g);
        auto s = UIKit::hbox(8);
        s->add(UIKit::icon("assets/icons/soul_shard.png", 48));
        shards_label = UIKit::label("", UIKit::T_NAME, Col("#d0a8ff"), ALIGN_LEFT, 8);
        s->add(shards_label);
        cur->add(s);
        col->add(cur);
        auto btns = UIKit::hbox(16);
        btns->alignment = ALIGNMENT_CENTER;
        auto one = FantasyButton::make(UIKit::fmt("SUMMON x1\n%d", I(banner, "single_cost", 100)), "steel", Vec2(440, 150),
                                       "assets/icons/gem.png");
        one->set_name("SummonOne");
        one->set_font_size(34);
        one->pressed.connect([this] { summon(1); });
        btns->add(one);
        int multi = I(banner, "multi_count", 10);
        auto ten = FantasyButton::make(UIKit::fmt("SUMMON x%d\n%d", multi, I(banner, "multi_cost", 1000)), "ember", Vec2(440, 150),
                                       "assets/icons/gem.png");
        ten->set_name("SummonTen");
        ten->set_font_size(34);
        ten->add_shine();
        ten->pressed.connect([this, multi] { summon(multi); });
        btns->add(ten);
        col->add(btns);
        col->add(UIKit::label("Heroes you already own become Soul Shards (used for Burst training).", UIKit::T_SMALL, UIKit::MUTED,
                              ALIGN_CENTER, 4));
        refresh();
        AudioManager::play_music("summon");
        listen(this, GM.profile_changed, [this] { refresh(); });
    }

    static std::string pct(double v)
    {
        std::string s = UIKit::fmt("%.1f%%", v * 100.0);
        auto p = s.find(".0%");
        if (p != std::string::npos) s.replace(p, 3, "%");
        return s;
    }

    void refresh()
    {
        if (!gems_label) return;
        gems_label->set_text(UIKit::format_number(GM.gems()));
        shards_label->set_text(UIKit::format_number(GM.soul_shards()));
    }

    // ------------------------------------------------------------------ details
    void open_details()
    {
        auto p = FantasyPopup::open(this, "SUMMON DETAILS", 1000);
        p->set_name("SummonDetailsPopup");
        auto scroll = ScrollContainer::create();
        scroll->set_custom_min(Vec2(940, 1100));
        p->content->add(scroll);
        auto v = UIKit::vbox(10);
        v->set_h_flags(SIZE_EXPAND_FILL);
        scroll->add(v);
        v->add(UIKit::label(S(banner, "name"), UIKit::T_NAME, UIKit::GOLD, ALIGN_CENTER, 8));
        std::string costs = UIKit::fmt("Single: %d Gems     x%d: %d Gems", I(banner, "single_cost", 100), I(banner, "multi_count", 10),
                                       I(banner, "multi_cost", 1000));
        v->add(UIKit::label(costs, UIKit::T_BODY, Col("#9ae8ff"), ALIGN_CENTER, 6));
        v->add(UIKit::label("RARITY RATES", UIKit::T_BODY, UIKit::SKY, ALIGN_LEFT, 6));
        Json rr = SummonSystem::rates(banner);
        for (int r : {5, 4, 3})
        {
            auto h = UIKit::hbox(10);
            h->add(UIKit::stars(r, 32));
            h->add(UIKit::spacer());
            h->add(UIKit::label(pct(F(rr, std::to_string(r), 0.0)), UIKit::T_BODY, rarity_color(r), ALIGN_RIGHT, 6));
            v->add(h);
        }
        v->add(UIKit::separator());
        v->add(UIKit::label("HEROES IN THIS GATE (chance per summon)", UIKit::T_BODY, UIKit::SKY, ALIGN_LEFT, 6));
        Json hr = SummonSystem::hero_rates(banner);
        std::vector<std::string> ids;
        for (auto& [k, _] : hr.items()) ids.push_back(k);
        std::sort(ids.begin(), ids.end(), [](const std::string& a, const std::string& b) {
            int ra = I(DB.character(a), "rarity", 3), rb = I(DB.character(b), "rarity", 3);
            return ra > rb || (ra == rb && a < b);
        });
        for (auto& cid : ids)
        {
            const Json& d = DB.character(cid);
            auto h = UIKit::hbox(10);
            h->add(UIKit::orb(S(d, "element"), 36));
            auto n = UIKit::label(S(d, "name"), UIKit::T_SMALL, UIKit::TEXT, ALIGN_LEFT, 5);
            n->set_h_flags(SIZE_EXPAND_FILL);
            h->add(n);
            h->add(UIKit::stars(I(d, "rarity", 3), 20));
            h->add(UIKit::label(UIKit::fmt("%.2f%%", F(hr, cid, 0.0) * 100.0), UIKit::T_SMALL, UIKit::GOLD, ALIGN_RIGHT, 5));
            if (GM.owns_family(S(d, "family"))) h->add(UIKit::tag("OWNED", Col("#2a5a9a")));
            v->add(h);
        }
        v->add(UIKit::separator());
        const Json& ds = O(DB.summon, "duplicate_shards");
        for (auto& line : {std::string("DUPLICATES"),
                           std::string("If you already own a hero of the same line (any form), the summon becomes Soul Shards instead:"),
                           UIKit::fmt("3* = %d   4* = %d   5* = %d Soul Shards", I(ds, "3", 10), I(ds, "4", 30), I(ds, "5", 100)),
                           std::string("Soul Shards train any hero's Burst level. No hero ever needs duplicates to evolve."),
                           std::string("Gems come from first clears, rank-ups, missions and login rewards. Nothing here can be bought with money.")})
        {
            auto w = UIKit::wrap_label(line, UIKit::T_SMALL, UIKit::TEXT);
            w->set_min_w(900);
            v->add(w);
        }
        auto close = FantasyButton::make("CLOSE", "ember", Vec2(300, 100));
        close->set_h_flags(SIZE_SHRINK_CENTER);
        close->pressed.connect([p] { p->close(); });
        p->content->add(close);
    }

    // ------------------------------------------------------------------ summoning
    void summon(int count)
    {
        if (busy) return;
        int cost = count == 1 ? I(banner, "single_cost", 100) : I(banner, "multi_cost", 1000);
        if (GM.gems() < cost)
        {
            UIManager::not_enough("Gems", cost, GM.gems(), "Earn Gems from first clears, rank-ups, missions and login rewards.");
            return;
        }
        ConfirmOpts o;
        o.name = "SummonConfirm";
        o.lines = {{"assets/icons/gem.png", "Cost  " + UIKit::format_number(cost) + " Gems", Col("#9ae8ff")},
                   {"", "Gems left after:  " + UIKit::format_number(GM.gems() - cost), UIKit::MUTED}};
        UIManager::confirm(UIKit::fmt("SUMMON x%d?", count), "", "SUMMON", [this, count] { do_summon(count); }, o);
    }

    void do_summon(int count)
    {
        busy = true;
        bool first_time = I(O(GM.profile, "summon"), "total", 0) == 0;
        Json r = GM.summon("standard", count);
        if (!B(r, "ok", false))
        {
            busy = false;
            UIManager::toast(S(r, "reason", "The gate did not answer."), "error");
            return;
        }
        refresh();
        auto ceremony = gd::make<SummonCeremony>();
        ceremony->set_name("SummonCeremony");
        add(ceremony);
        Json results = A(r, "results");
        // the ceremony only runs while it (and this screen) is in the tree
        ceremony->finished.connect([this, ceremony, results] {
            ceremony->queue_free();
            busy = false;
            show_results(results);
        });
        ceremony->play(results, !first_time);
    }

    void show_results(const Json& results)
    {
        bool multi = results.size() > 1;
        auto p = FantasyPopup::open(this, "SUMMON RESULTS", 1020);
        p->set_name("SummonResults");
        auto grid = GridContainer::create(multi ? 5 : 1);
        grid->h_separation = 10;
        grid->v_separation = 10;
        grid->set_h_flags(SIZE_SHRINK_CENTER);
        p->content->add(grid);
        int shards = 0;
        std::vector<std::string> new_ones;
        for (auto& e : results)
        {
            const Json& d = DB.character(S(e, "char_id"));
            auto cell = PanelFrame::make(UIKit::fmt("rarity_%d", std::clamp(I(e, "rarity", 3), 3, 6)), 6);
            cell->set_name("Result_" + S(e, "char_id"));
            float px = multi ? 170 : 360;
            auto v = UIKit::vbox(2);
            v->set_mouse_filter(MOUSE_IGNORE);
            cell->add(v);
            auto art = UIKit::portrait_art(d, Vec2(px, px));
            v->add(art);
            std::string name = S(d, "name");
            v->add(UIKit::label(name.substr(0, name.find(' ')), UIKit::T_SMALL, UIKit::TEXT, ALIGN_CENTER, 5));
            auto st = UIKit::stars(I(e, "rarity", 3), multi ? 18 : 32);
            st->set_position(Vec2(4, px - (multi ? 22 : 36)));
            art->add(st);
            if (B(e, "is_new", false))
            {
                auto nt = UIKit::tag("NEW!", Col("#c8281e"));
                nt->set_position(Vec2(4, 4));
                art->add(nt);
                std::string uid = S(e, "uid");
                new_ones.push_back(uid);
                UIKit::on_tap(cell, [this, uid] { new_hero_popup(uid); });
            }
            else
            {
                // duplicates are marked clearly and show exactly what they became
                auto dt = UIKit::tag("DUPLICATE", Col("#5a3a8a"));
                dt->set_position(Vec2(4, 4));
                art->add(dt);
                art->set_modulate(Col(0.8f, 0.78f, 0.85f));
                shards += I(e, "shards", 0);
                auto sh = UIKit::hbox(2);
                sh->alignment = ALIGNMENT_CENTER;
                sh->set_mouse_filter(MOUSE_IGNORE);
                sh->add(UIKit::icon("assets/icons/soul_shard.png", 24));
                sh->add(UIKit::label(UIKit::fmt("+%d", I(e, "shards", 0)), UIKit::T_SMALL, Col("#d0a8ff"), ALIGN_CENTER, 5));
                v->add(sh);
                Json entry = e;
                UIKit::on_tap(cell, [this, entry] { duplicate_popup(entry); });
            }
            grid->add(cell);
        }
        if (shards > 0)
        {
            auto w = UIKit::wrap_label(UIKit::fmt("Duplicates were converted into %d Soul Shards - use them to train any hero's Burst.", shards),
                                       UIKit::T_SMALL, Col("#d0a8ff"));
            w->h_align = ALIGN_CENTER;
            w->set_min_w(940);
            p->content->add(w);
        }
        p->content->add(UIKit::label(std::string("Tap a hero to inspect it.") + (new_ones.empty() ? "" : " NEW heroes can join your squad."),
                                     UIKit::T_SMALL, UIKit::GOLD, ALIGN_CENTER, 5));
        auto row = UIKit::hbox(14);
        row->alignment = ALIGNMENT_CENTER;
        if (new_ones.size() == 1) add_new_hero_buttons(row, new_ones[0], p);
        auto cont = FantasyButton::make("CONTINUE", "ember", Vec2(300, 116));
        cont->set_name("ResultsContinue");
        cont->pressed.connect([p] { p->close(); });
        row->add(cont);
        p->content->add(row);
        p->default_action = [p] { p->close(); };
    }

    void add_new_hero_buttons(Control* row, const std::string& uid, FantasyPopup* popup)
    {
        auto det = FantasyButton::make("DETAILS", "steel", Vec2(260, 116));
        det->set_name("NewHeroDetails");
        det->pressed.connect([popup, uid] {
            popup->close();
            SceneRouter::go("unit_detail", {{"uid", uid}, {"back", "summon"}});
        });
        row->add(det);
        auto add_b = FantasyButton::make("ADD TO SQUAD", "gold", Vec2(340, 116));
        add_b->set_name("NewHeroAdd");
        add_b->set_disabled(GM.is_in_party(uid) || !GM.feature_unlocked("squad"));
        add_b->pressed.connect([popup, uid, add_b] {
            if ((int)GM.party_uids().size() >= GM.max_party_size())
            {
                popup->close();
                UIManager::toast("Your squad is full - choose who to swap out.", "info");
                SceneRouter::go("squad");
            }
            else if (GM.toggle_party(uid))
            {
                add_b->set_disabled(true);
                add_b->set_text("IN SQUAD");
                AudioManager::play_sfx("unit_select");
                UIManager::toast("Added to your squad.", "success");
            }
        });
        row->add(add_b);
    }

    // Inspecting a duplicate result: which hero, and what it turned into.
    void duplicate_popup(const Json& e)
    {
        const Json& d = DB.character(S(e, "char_id"));
        auto p = FantasyPopup::open(this, "DUPLICATE", 860);
        p->set_name("DuplicatePopup");
        p->tap_outside_closes = true;
        auto fr = PanelFrame::make(UIKit::fmt("rarity_%d", std::clamp(I(e, "rarity", 3), 3, 6)), 6);
        fr->set_h_flags(SIZE_SHRINK_CENTER);
        fr->add(UIKit::portrait_art(d, Vec2(240, 240)));
        p->content->add(fr);
        p->content->add(UIKit::label(S(d, "name"), UIKit::T_NAME, UIKit::GOLD, ALIGN_CENTER, 8));
        auto w = UIKit::wrap_label("You already have a hero of this line, so this summon became Soul Shards.", UIKit::T_BODY);
        w->h_align = ALIGN_CENTER;
        w->set_min_w(780);
        p->content->add(w);
        auto h = UIKit::hbox(UIKit::SP_S);
        h->alignment = ALIGNMENT_CENTER;
        h->add(UIKit::icon("assets/icons/soul_shard.png", 56));
        h->add(UIKit::label(UIKit::fmt("+%d Soul Shards", I(e, "shards", 0)), UIKit::T_NAME, Col("#d0a8ff"), ALIGN_LEFT, 8));
        p->content->add(h);
        p->content->add(UIKit::label("Spend them on any hero's Burst level (Unit Details).", UIKit::T_SMALL, UIKit::MUTED, ALIGN_CENTER, 5));
        auto ok = UIKit::btn("OK", "primary", Vec2(260, 100));
        ok->set_h_flags(SIZE_SHRINK_CENTER);
        ok->pressed.connect([p] { p->close(); });
        p->content->add(ok);
        p->default_action = [p] { p->close(); };
    }

    void new_hero_popup(const std::string& uid)
    {
        Json u = GM.unit(uid);
        const Json& d = DB.character(S(u, "char_id"));
        auto p = FantasyPopup::open(this, "NEW HERO", 900);
        p->set_name("NewHeroPopup");
        p->content->add(UIKit::label(S(d, "name"), UIKit::T_NAME, UIKit::GOLD, ALIGN_CENTER, 8));
        auto s = UIKit::stars(I(d, "rarity", 3), 40);
        s->alignment = ALIGNMENT_CENTER;
        p->content->add(s);
        auto w = UIKit::wrap_label(S(d, "role") + "  -  " + S(d, "description"), UIKit::T_SMALL, Col("#e0d6c6"));
        w->set_min_w(820);
        w->h_align = ALIGN_CENTER;
        p->content->add(w);
        auto row = UIKit::hbox(12);
        row->alignment = ALIGNMENT_CENTER;
        add_new_hero_buttons(row, uid, p);
        auto c = FantasyButton::make("CONTINUE", "stone", Vec2(260, 116));
        c->pressed.connect([p] { p->close(); });
        row->add(c);
        p->content->add(row);
    }
};
REGISTER_SCREEN("summon", SummonScreen)
