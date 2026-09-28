// Title screen (scripts/ui/main_menu.gd): key art, logo, CONTINUE / NEW GAME / SETTINGS / EXIT.
#include "screens/Screens.h"

class MainMenu : public ScreenBase
{
public:
    FantasyButton* btn_continue = nullptr;

    void ready() override
    {
        UIKit::screen_background(this, "bg_title", 0.0f);
        add_embers();
        add_key_art();

        auto top = UIKit::vbox(0);
        top->set_anchors_preset(gd::PRESET_TOP_WIDE);
        top->set_offset(gd::SIDE_TOP, 150);
        add(top);
        auto logo = UIKit::heading("CINDERBOUND", 130, Col("#ffb04a"));
        logo->set_outline(22, Col("#3a0e08"));
        top->add(logo);
        auto sub = UIKit::title_plate("EMBERS OF THE ASHROOT WILDS", 30);
        sub->set_min_w(760);
        top->add(sub);
        auto tw = gd::tween(logo);
        tw->loops();
        tw->alpha(logo, 0.85f, 1.2f).trans(gd::TRANS_SINE);
        tw->alpha(logo, 1.0f, 1.2f).trans(gd::TRANS_SINE);

        auto buttons = UIKit::vbox(22);
        buttons->set_anchors_preset(gd::PRESET_CENTER_BOTTOM);
        buttons->set_offsets(-320, -700, 320, -140);
        add(buttons);
        btn_continue = UIKit::button("CONTINUE", "", Vec2(640, 130), "ember");
        auto btn_new = UIKit::button("NEW GAME", "", Vec2(640, 130), "gold");
        auto btn_settings = UIKit::button("SETTINGS", "assets/icons/nav_settings.png", Vec2(640, 110));
        auto btn_exit = UIKit::button("EXIT", "", Vec2(640, 110), "stone");
        for (FantasyButton* b : {btn_continue, btn_new, btn_settings, btn_exit})
        {
            b->set_font_size(b->custom_min().y > 120 ? 50 : 40);
            buttons->add(b);
        }
        btn_continue->set_name("ContinueButton");
        btn_new->set_name("NewGameButton");
        btn_continue->pressed.connect([this] { on_continue(); });
        btn_continue->add_shine();
        btn_new->pressed.connect([this] { on_new_game(); });
        btn_settings->pressed.connect([this] { SettingsPanel::open(this); });
        btn_exit->pressed.connect([] { App::quit_game(0); });
        btn_continue->set_disabled(!GM.can_continue());

        auto ver = UIKit::label("Prototype v0.6.0  -  original art & audio", 20, Col(1, 1, 1, 0.6f), gd::ALIGN_CENTER);
        ver->set_anchors_preset(gd::PRESET_BOTTOM_WIDE);
        ver->set_offsets(0, -70, 0, -30);
        add(ver);

        AudioManager::play_music("menu");
        const std::string& st = SaveManager::get().last_load_status;
        if (st == "corrupted")
            UIKit::message(this, "Save Problem",
                           "Your save file could not be read and no backup was found. You can start a new game; settings are unaffected.");
        else if (st == "recovered_backup")
            UIKit::toast(this, "Save restored from backup", UIKit::GOLD);
    }

    void add_key_art()
    {
        auto glow = gd::ColorRect::create(Col(1.0f, 0.45f, 0.15f, 0.10f));
        glow->set_anchors_preset(gd::PRESET_FULL_RECT);
        glow->set_mouse_filter(gd::MOUSE_IGNORE);
        add(glow);
        struct Pose { const char* id; Vec2 at; float k; const char* anim; };
        for (auto p : {Pose{"mira_tidesong", Vec2(-300, 1180), 10, "idle"}, Pose{"thorne_mossguard", Vec2(300, 1190), 10, "idle"},
                       Pose{"kael_emberclaw", Vec2(0, 1250), 12, "victory"}})
        {
            auto d = UnitSpriteDisplay::make(O(DB.character(p.id), "sprite"), p.k, p.at.x > 0, p.anim);
            Vec2 m = d->custom_min();
            d->set_position(Vec2(540 + p.at.x - m.x / 2, p.at.y - m.y));
            d->set_size(m);
            add(d);
        }
    }

    void add_embers()
    {
        gd::ParticleCfg c;
        c.amount = 70;
        c.lifetime = 7.0f;
        c.emission_rect = Vec2(600, 10);
        c.direction = Vec2(0, -1);
        c.spread = 25;
        c.gravity = Vec2(0, -8);
        c.vel_min = 80;
        c.vel_max = 170;
        c.scale_min = 5;
        c.scale_max = 9;
        c.ramp = {Col("#ffd35a"), Col(1, 0.3f, 0.1f, 0)};
        c.preprocess = 3;
        auto p = gd::Particles::create(c);
        p->set_position(Vec2(540, 1980));
        add(p);
    }

    void on_continue()
    {
        if (GM.continue_game())
            SceneRouter::go("home");
        else
        {
            btn_continue->set_disabled(true);
            UIKit::message(this, "No Save Found", "There is no saved journey yet. Choose NEW GAME to begin.");
        }
    }

    void on_new_game()
    {
        if (GM.can_continue())
            UIKit::confirm(this, "Start a new journey? Your current progress will be erased.",
                           [] { SceneRouter::go("starter_select"); }, "NEW GAME", "CANCEL");
        else
            SceneRouter::go("starter_select");
    }
};
REGISTER_SCREEN("main_menu", MainMenu)
