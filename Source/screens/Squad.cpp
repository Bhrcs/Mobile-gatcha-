// Squad editor (scripts/ui/squad.gd). Tap a slot to select it; tap another slot to swap;
// use the actions below. Reserve heroes are added with a tap.
#include "screens/Screens.h"

using namespace UIKit;
using gd::Rect2;

class SquadScreen : public ScreenBase
{
public:
    gd::BoxContainer* slots_row = nullptr;
    gd::GridContainer* bench = nullptr;
    gd::BoxContainer* action_row = nullptr;
    gd::Label* info = nullptr;
    gd::Label* leader_label = nullptr;
    gd::Label* power_label = nullptr;
    int selected = -1;
    std::string stage_id;   // set when opened from a stage's PREPARE
    gd::BoxContainer* matchup = nullptr;

    void ready() override
    {
        if (!require_profile()) return;
        std::string back_to = S(params(), "from_uid"), return_to = S(params(), "return_to");
        stage_id = S(params(), "stage_id");
        if (!return_to.empty())
            back_fallback = return_to;
        else if (!back_to.empty())
            back_fallback = "units";
        auto area = build_frame("bg_camp", "SQUAD", "units", nullptr, 0.6f, true, {{"help", "squad"}});
        auto col = vbox(14);
        col->set_anchors_preset(gd::PRESET_FULL_RECT);
        area->add(col);

        auto party_panel = PanelFrame::make("panel", 22);
        col->add(party_panel);
        auto pv = vbox(12);
        party_panel->add(pv);
        pv->add(label(UIKit::fmt("PARTY  (MAX %d)", GM.max_party_size()), T_BODY, GOLD, gd::ALIGN_LEFT, 6));
        slots_row = hbox(10);
        slots_row->alignment = gd::ALIGNMENT_CENTER;
        pv->add(slots_row);
        auto lrow = hbox(10);
        lrow->add(icon("assets/icons/leader.png", 40));
        leader_label = wrap_label("", T_SMALL, GOLD);
        leader_label->set_name("LeaderSkill");
        leader_label->set_h_flags(gd::SIZE_EXPAND_FILL);
        lrow->add(leader_label);
        power_label = label("", T_BODY, TEXT, gd::ALIGN_RIGHT, 6);
        power_label->set_name("SquadPower");
        lrow->add(power_label);
        pv->add(lrow);
        info = label("", T_BODY, MUTED, gd::ALIGN_CENTER);
        pv->add(info);
        action_row = hbox(12);
        action_row->alignment = gd::ALIGNMENT_CENTER;
        pv->add(action_row);
        matchup = vbox(0);
        pv->add(matchup);

        col->add(label("RESERVE", T_BODY, GOLD, gd::ALIGN_LEFT, 6));
        auto scroll = gd::ScrollContainer::create();
        scroll->set_v_flags(gd::SIZE_EXPAND_FILL);
        col->add(scroll);
        auto center = gd::CenterContainer::create();
        center->set_h_flags(gd::SIZE_EXPAND_FILL);
        scroll->add(center);
        bench = gd::GridContainer::create(4);
        bench->h_separation = 12;
        bench->v_separation = 12;
        center->add(bench);
        refresh();
    }

    int slot_width()
    {
        int n = GM.max_party_size();
        return std::clamp((1000 - (n - 1) * 10) / n, 180, 330);
    }

    void refresh()
    {
        slots_row->clear_children();
        bench->clear_children();
        action_row->clear_children();
        Json party = GM.party_units();
        Json ls = GM.leader_skill();
        leader_label->set_text(ls.empty() ? "" : "LEADER SKILL: " + S(ls, "name") + " - " + S(ls, "description"));
        power_label->set_text("POWER " + format_number(GM.squad_power()));
        matchup->clear_children();
        if (!stage_id.empty() && !DB.stage(stage_id).empty())
            matchup->add(StageInfo::matchup_row(party, DB.stage(stage_id), this));
        int w = slot_width();
        for (int i = 0; i < GM.max_party_size(); i++)
            slots_row->add(slot(i < (int)party.size() ? party[i] : Json::object(), i, w));
        bool any_bench = false;
        Json owned = GM.units();
        for (auto& u : owned)
        {
            std::string uid = S(u, "uid");
            if (GM.is_in_party(uid)) continue;
            any_bench = true;
            auto card = UnitCard::make(u);
            card->tapped.connect([this, uid](std::string) { add_unit(uid); });
            bench->add(card);
        }
        if (!any_bench)
        {
            auto l = wrap_label("Every hero you own is already in the party. New heroes will appear here.", T_BODY, MUTED);
            l->set_min_w(900);
            l->set_align(gd::ALIGN_CENTER);
            bench->add(l);
        }
        if (selected >= 0 && selected < (int)party.size())
        {
            std::string uid = S(party[selected], "uid");
            info->set_text(S(DB.character(S(party[selected], "char_id")), "name") + " selected - tap another slot to swap");
            if (selected > 0)
            {
                auto lead = FantasyButton::make("MAKE LEADER", "gold", Vec2(380, 104), "assets/icons/leader.png");
                lead->set_name("MakeLeader");
                lead->set_font_size(30);
                lead->pressed.connect([this, uid] {
                    GM.set_leader(uid);
                    AudioManager::play_sfx("unit_select");
                    UIManager::toast(S(DB.character(S(GM.unit(uid), "char_id")), "name") + " now leads the squad.", "success");
                    selected = 0;
                    refresh();
                });
                action_row->add(lead);
            }
            auto rem = FantasyButton::make("REMOVE", "stone", Vec2(260, 104));
            rem->set_font_size(30);
            rem->set_disabled(party.size() <= 1);
            rem->pressed.connect([this, uid] {
                GM.toggle_party(uid);
                selected = -1;
                refresh();
            });
            action_row->add(rem);
            auto view = FantasyButton::make("DETAILS", "steel", Vec2(260, 104));
            view->set_font_size(30);
            view->pressed.connect([uid] { SceneRouter::go("unit_detail", {{"uid", uid}}); });
            action_row->add(view);
        }
        else
        {
            selected = -1;
            info->set_text("Tap a hero to select. The leader stands at the front.");
        }
    }

    gd::Control* slot(const Json& u, int index, int w)
    {
        bool leader = index == 0;
        auto v = vbox(6);
        v->set_name(UIKit::fmt("Slot_%d", index));
        auto head = hbox(6);
        head->alignment = gd::ALIGNMENT_CENTER;
        if (leader) head->add(icon("assets/icons/leader.png", 48));
        head->add(label(leader ? "LEADER" : UIKit::fmt("SLOT %d", index + 1), T_SMALL, leader ? GOLD : MUTED, gd::ALIGN_CENTER, 5));
        v->add(head);
        PanelFrame* frame;
        if (u.empty())
        {
            frame = PanelFrame::make("inset", 12);
            frame->set_custom_min(Vec2(w, w * 1.2f));
            auto l = label("EMPTY", T_BODY, MUTED, gd::ALIGN_CENTER);
            l->set_align(gd::ALIGN_CENTER, gd::VALIGN_CENTER);
            frame->add(l);
        }
        else
        {
            const Json& def = DB.character(S(u, "char_id"));
            std::string el = S(def, "element", "neutral");
            frame = PanelFrame::make("card_" + el + (index == selected ? "_lit" : ""), 10);
            frame->set_custom_min(Vec2(w, w * 1.2f));
            auto stack = vbox(4);
            stack->set_mouse_filter(gd::MOUSE_IGNORE);
            frame->add(stack);
            stack->add(portrait_art(def, Vec2(w - 20, w - 40)));
            auto row = hbox(6);
            row->alignment = gd::ALIGNMENT_CENTER;
            row->add(orb(el, 32));
            std::string name = S(def, "name");
            row->add(label(UIKit::fmt("%s Lv%d", name.substr(0, name.find(' ')).c_str(), I(u, "level", 1)), T_SMALL, TEXT,
                           gd::ALIGN_LEFT, 5));
            stack->add(row);
            if (index == selected) frame->set_modulate(Col(1.1f, 1.08f, 0.95f));   // clamps to (1, 1, 0.95)
        }
        if (leader) sparkle(frame, Rect2{Vec2(0, 0), Vec2(w, w * 1.2f)}, Col("#ffd35a"), 5);
        on_tap(frame, [this, index] { on_slot(index); });
        v->add(frame);
        return v;
    }

    void on_slot(int index)
    {
        int size = (int)GM.party_uids().size();
        if (index >= size)
        {
            selected = -1;
            refresh();
            return;
        }
        if (selected >= 0 && selected != index)
        {
            GM.swap_party_slots(selected, index);
            AudioManager::play_sfx("unit_select");
            selected = -1;
        }
        else
        {
            selected = selected != index ? index : -1;
            AudioManager::play_sfx("unit_select", 0.03f, -4.0f);
        }
        refresh();
    }

    void add_unit(const std::string& uid)
    {
        if ((int)GM.party_uids().size() >= GM.max_party_size())
        {
            UIManager::toast("The squad is full. Select a squad slot and REMOVE a hero first.", "warning");
            return;
        }
        GM.toggle_party(uid);
        AudioManager::play_sfx("unit_select");
        refresh();
    }
};
REGISTER_SCREEN("squad", SquadScreen)
