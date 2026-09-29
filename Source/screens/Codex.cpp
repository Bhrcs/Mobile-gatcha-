// Hero Codex (scripts/ui/codex.gd): every hero line in the realm. Owned heroes show their
// art, element, rarity path and lore; unknown heroes are silhouettes with only their element.
#include "screens/Screens.h"

using namespace UIKit;

class CodexScreen : public ScreenBase
{
public:
    gd::GridContainer* grid = nullptr;

    void ready() override
    {
        if (!require_profile()) return;
        back_fallback = "units";
        auto area = build_frame("bg_camp", "CODEX", "units", nullptr, 0.6f);
        auto col = vbox(12);
        col->set_anchors_preset(gd::PRESET_FULL_RECT);
        area->add(col);
        const Json& owned = A(GM.profile, "codex");
        auto fams = DB.family_ids();
        auto head = PanelFrame::make("plank", 12);
        auto hh = hbox(12);
        head->add(hh);
        hh->add(icon("assets/icons/codex.png", 56));
        auto t = label(UIKit::fmt("OWNED  %d / %d", (int)owned.size(), (int)fams.size()), T_NAME, GOLD, gd::ALIGN_LEFT, 8);
        t->set_name("CodexCount");
        t->set_h_flags(gd::SIZE_EXPAND_FILL);
        hh->add(t);
        hh->add(label("Find more heroes at the Embergate.", T_SMALL, MUTED, gd::ALIGN_RIGHT, 5));
        col->add(head);
        auto scroll = gd::ScrollContainer::create();
        scroll->set_v_flags(gd::SIZE_EXPAND_FILL);
        col->add(scroll);
        auto center = gd::CenterContainer::create();
        center->set_h_flags(gd::SIZE_EXPAND_FILL);
        scroll->add(center);
        grid = gd::GridContainer::create(4);
        grid->h_separation = 12;
        grid->v_separation = 12;
        center->add(grid);
        for (auto& cid : fams)
        {
            const Json& d = DB.character(cid);
            grid->add(entry(d, contains(owned, at(d, "family"))));
        }
        AudioManager::play_music("menu");
    }

    gd::Control* entry(const Json& d, bool known)
    {
        std::string el = S(d, "element", "neutral");
        auto p = PanelFrame::make(known ? "card_" + el : "inset", 10);
        p->set_name("Codex_" + S(d, "family"));
        p->set_custom_min(Vec2(244, 320));
        auto v = vbox(4);
        v->set_mouse_filter(gd::MOUSE_IGNORE);
        p->add(v);
        auto art = portrait_art(d, Vec2(216, 216));
        if (!known)
        {
            // portrait_art: [0] gradient backdrop, then the portrait
            auto kids = art->children();
            for (size_t i = 0; i < kids.size(); i++)
                kids[i]->set_modulate(i == 0 ? Col(0.25f, 0.25f, 0.3f) : Col(0, 0, 0, 0.9f));   // silhouette
        }
        v->add(art);
        std::string name = S(d, "name");
        v->add(label(known ? name.substr(0, name.find(' ')) : "? ? ?", T_SMALL, known ? TEXT : MUTED, gd::ALIGN_CENTER, 5));
        auto row = hbox(4);
        row->alignment = gd::ALIGNMENT_CENTER;
        row->add(orb(el, 28));
        if (known)
        {
            Json forms = DB.family_forms(S(d, "family"));
            const Json& top = forms.empty() ? d : DB.character(S(forms.back()));
            row->add(label(UIKit::fmt("%d-%d*", I(d, "rarity", 3), I(top, "rarity", 3)), T_SMALL, GOLD, gd::ALIGN_LEFT, 5));
        }
        v->add(row);
        if (known)
            on_tap(p, [this, d] { details(d); });
        else
            on_tap(p, [this, el] {
                toast(this, "An unknown " + DB.element_name(el) + " hero. Summon at the Embergate to meet them.", MUTED);
            });
        return p;
    }

    void details(const Json& d)
    {
        auto p = FantasyPopup::open(this, upper(S(d, "name")), 1000);
        p->set_name("CodexDetails");
        auto row = hbox(10);
        row->alignment = gd::ALIGNMENT_CENTER;
        Json forms = DB.family_forms(S(d, "family"));
        for (size_t i = 0; i < forms.size(); i++)
        {
            const Json& fd = DB.character(S(forms[i]));
            auto cell = vbox(2);
            auto frame = PanelFrame::make("rarity_" + std::to_string(std::clamp(I(fd, "rarity", 3), 3, 6)), 6);
            frame->add(portrait_art(fd, Vec2(220, 220)));
            cell->add(frame);
            auto n = label(S(fd, "name"), T_SMALL, TEXT, gd::ALIGN_CENTER, 5);
            n->set_min_w(240);
            n->set_clip_text(true);
            cell->add(n);
            auto s = stars(I(fd, "rarity", 3), 24);
            s->alignment = gd::ALIGNMENT_CENTER;
            cell->add(s);
            row->add(cell);
            if (i < forms.size() - 1) row->add(label(">", T_HEAD, EMBER, gd::ALIGN_CENTER, 6));
        }
        p->content->add(row);
        for (auto& line : {S(d, "role") + "  -  " + DB.element_name(S(d, "element")),
                           "Burst: " + S(DB.skill(S(d, "burst")), "name"),
                           "Passive: " + S(O(d, "passive"), "description"),
                           "Leader: " + S(O(d, "leader_skill"), "description"), S(d, "lore")})
        {
            auto w = wrap_label(line, T_SMALL, Col("#e0d6c6"));
            w->set_min_w(920);
            p->content->add(w);
        }
        // GameManager.unit_of_family (no C++ equivalent)
        std::string uid;
        for (auto& u : GM.units())
            if (S(DB.character(S(u, "char_id")), "family") == S(d, "family")) { uid = S(u, "uid"); break; }
        auto br = hbox(14);
        br->alignment = gd::ALIGNMENT_CENTER;
        if (!uid.empty())
        {
            auto go = FantasyButton::make("VIEW HERO", "ember", Vec2(320, 110));
            go->pressed.connect([p, uid] {
                p->close();
                SceneRouter::go("unit_detail", {{"uid", uid}, {"back", "codex"}});
            });
            br->add(go);
        }
        auto close = FantasyButton::make("CLOSE", "stone", Vec2(260, 110));
        close->pressed.connect([p] { p->close(); });
        br->add(close);
        p->content->add(br);
    }
};
REGISTER_SCREEN("codex", CodexScreen)
