// Player profile (scripts/ui/profile.gd): name (editable), rank, energy, currencies, collection and
// progress (stars per world, tower floors) and battle statistics.
#include "screens/Screens.h"
#include <ctime>

using namespace gd;

// LineEdit fixes its font size at init; this re-applies `font_size` to the text field.
namespace {
class NameEdit : public LineEdit
{
public:
    void apply_font_size()
    {
        auto cfg = _field->getTTFConfig();
        cfg.fontSize = (float)font_size;
        _field->setTTFConfig(cfg);
    }
};
}  // namespace

static std::string strip(const std::string& s)
{
    size_t a = s.find_first_not_of(" \t\n\r"), b = s.find_last_not_of(" \t\n\r");
    return a == std::string::npos ? "" : s.substr(a, b - a + 1);
}

class ProfileScreen : public ScreenBase
{
public:
    BoxContainer* body = nullptr;

    void ready() override
    {
        if (!require_profile()) return;
        auto area = build_frame("bg_camp", "PROFILE", "profile", nullptr, 0.6f);
        auto scroll = ScrollContainer::create();
        scroll->set_anchors_preset(PRESET_FULL_RECT);
        area->add(scroll);
        body = UIKit::vbox(12);
        body->set_h_flags(SIZE_EXPAND_FILL);
        scroll->add(body);
        build();
    }

    void build()
    {
        body->clear_children();
        const Json& pl = O(GM.profile, "player");
        // identity
        auto head = PanelFrame::make("panel", 20);
        body->add(head);
        auto hh = UIKit::hbox(18);
        head->add(hh);
        Json leader = GM.unit(GM.leader_uid());
        if (!leader.is_null() && !leader.empty())
        {
            const Json& def = DB.character(S(leader, "char_id"));
            auto fr = PanelFrame::make(UIKit::fmt("rarity_%d", std::clamp(I(def, "rarity", 3), 3, 6)), 6);
            fr->add(UIKit::portrait_art(def, Vec2(200, 200)));
            hh->add(fr);
        }
        auto v = UIKit::vbox(6);
        v->set_h_flags(SIZE_EXPAND_FILL);
        auto nm = UIKit::label(S(pl, "name", "Wayfarer"), UIKit::T_HEAD, Col("#fff0c0"), ALIGN_LEFT, 10);
        nm->set_name("PlayerName");
        v->add(nm);
        v->add(UIKit::label(UIKit::fmt("RANK %d", GM.rank()), UIKit::T_NAME, UIKit::GOLD, ALIGN_LEFT, 8));
        auto xb = ResourceBar::make("xp", 26);
        int need = Progression::rank_xp_to_next(GM.rank());
        int have = I(pl, "rank_xp", 0);
        xb->set_values((float)have, (float)need, false);
        v->add(xb);
        v->add(UIKit::label(UIKit::fmt("Rank EXP %d / %d   -   next Gem reward at Rank %d", have, need, next_gem_rank()), UIKit::T_SMALL,
                            UIKit::MUTED, ALIGN_LEFT, 5));
        hh->add(v);
        auto rn = FantasyButton::make("RENAME", "steel", Vec2(220, 90));
        rn->set_name("RenameButton");
        rn->set_font_size(28);
        rn->pressed.connect([this] { rename(); });
        hh->add(rn);

        using Rows = std::vector<std::pair<std::string, std::string>>;
        body->add(section("RESOURCES", Rows{{"Energy", UIKit::fmt("%d / %d", GM.energy(), GM.max_energy())},
                                            {"Gems", UIKit::format_number(GM.gems())},
                                            {"Gold", UIKit::format_number(GM.gold())},
                                            {"Soul Shards", UIKit::format_number(GM.soul_shards())}}));
        Rows story;
        for (auto& w : DB.world_order)
        {
            const Json& wd = O(DB.worlds, w);
            const Json& stages = A(wd, "stages");
            int cleared = 0;
            for (auto& st : stages)
                if (GM.is_stage_cleared(S(st, "id"))) ++cleared;
            int n = (int)stages.size();
            story.push_back({S(wd, "name", w), UIKit::fmt("%d / %d cleared   %d / %d stars", cleared, n, GM.total_stars(w), n * 3)});
        }
        for (auto& t : DB.tower_order)
        {
            const Json& td = O(DB.towers, t);
            story.push_back({S(td, "name", t), UIKit::fmt("Best floor %d / %d", GM.tower_highest_floor(t), (int)A(td, "stages").size())});
        }
        body->add(section("PROGRESS", story));
        const Json& stats = O(GM.profile, "stats");
        body->add(section("COLLECTION & RECORDS",
                          Rows{{"Heroes owned", std::to_string(GM.units().size())},
                               {"Codex", UIKit::fmt("%d / %d", (int)A(GM.profile, "codex").size(), (int)DB.family_ids().size())},
                               {"Battles won / lost", UIKit::fmt("%d / %d", I(stats, "battles_won", 0), I(stats, "battles_lost", 0))},
                               {"Enemies defeated", std::to_string(I(stats, "enemies_defeated", 0))},
                               {"Bosses defeated", std::to_string(I(stats, "bosses_defeated", 0))},
                               {"Summons", std::to_string(I(stats, "summons", 0))},
                               {"Login days", std::to_string(I(O(GM.profile, "login"), "total", 0))},
                               {"Play time", play_time(I(pl, "play_seconds", 0))},
                               {"Adventure began", date(I(pl, "created", 0))}}));
    }

    static int next_gem_rank()
    {
        int every = std::max(1, I(O(DB.progression, "rank_rewards"), "gems_every", 5));
        return (GM.rank() / every + 1) * every;
    }

    static Control* section(const std::string& title, const std::vector<std::pair<std::string, std::string>>& rows)
    {
        auto p = PanelFrame::make("plank", 16);
        std::string n = title;
        std::replace(n.begin(), n.end(), ' ', '_');
        p->set_name("Section_" + n);
        auto v = UIKit::vbox(6);
        p->add(v);
        v->add(UIKit::label(title, UIKit::T_BODY, UIKit::GOLD, ALIGN_LEFT, 6));
        for (auto& [k, val] : rows)
        {
            auto h = UIKit::hbox(10);
            auto l = UIKit::label(k, UIKit::T_BODY, UIKit::SKY, ALIGN_LEFT, 5);
            l->set_h_flags(SIZE_EXPAND_FILL);
            h->add(l);
            h->add(UIKit::label(val, UIKit::T_BODY, UIKit::TEXT, ALIGN_RIGHT, 5));
            v->add(h);
        }
        return p;
    }

    static std::string play_time(int s) { return UIKit::fmt("%dh %02dm", s / 3600, (s % 3600) / 60); }

    static std::string date(int ts)
    {
        if (ts <= 0) return "-";
        std::time_t t = ts;
        std::tm d = *std::gmtime(&t);
        return UIKit::fmt("%04d-%02d-%02d", d.tm_year + 1900, d.tm_mon + 1, d.tm_mday);
    }

    void rename()
    {
        auto p = FantasyPopup::open(this, "YOUR NAME", 860);
        p->set_name("RenamePopup");
        auto e = gd::make<NameEdit>();
        e->set_name("NameEdit");
        e->set_text(GM.player_name());
        e->max_length = 16;
        e->set_custom_min(Vec2(700, 90));
        e->font_size = UIKit::T_NAME;
        e->apply_font_size();
        e->set_h_flags(SIZE_SHRINK_CENTER);
        p->content->add(e);
        auto hint = UIKit::label("", UIKit::T_SMALL, UIKit::MUTED, ALIGN_CENTER, 5);
        hint->set_name("NameHint");
        p->content->add(hint);
        auto row = UIKit::hbox(14);
        row->alignment = ALIGNMENT_CENTER;
        auto c = UIKit::btn("CANCEL", "quiet", Vec2(280, 110));
        c->pressed.connect([p] { p->close(); });
        row->add(c);
        auto ok = UIKit::btn("SAVE", "primary", Vec2(280, 110));
        ok->set_name("SaveName");
        row->add(ok);
        p->content->add(row);
        // live validation: the reason is shown under the field, SAVE only when valid
        auto check = [hint, ok](const std::string& t) {
            std::string why = GameManager::validate_player_name(t);
            hint->set_text(!why.empty() ? why : UIKit::fmt("%d / 16", (int)strip(t).size()));
            hint->set_color(!why.empty() ? UIKit::EMBER : UIKit::MUTED);
            ok->set_disabled(!why.empty());
        };
        e->text_changed.connect(check);
        check(e->text());
        auto save = [this, p, e, ok] {
            if (ok->disabled()) return;
            GM.set_player_name(e->text());
            UIManager::toast("Name saved.", "success");
            p->close();
            build();
        };
        ok->pressed.connect(save);
        e->text_submitted.connect([save](std::string) { save(); });
        p->default_action = save;
        ax::RefPtr<NameEdit> keep(e);
        gd::defer([keep] { if (keep->is_inside_tree()) keep->grab_focus(); });
    }
};
REGISTER_SCREEN("profile", ProfileScreen)
