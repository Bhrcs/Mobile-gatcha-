#pragma once
// Pure progression maths: XP curves, stat growth, enemy scaling, loot rolls,
// training, Burst levels, power and the Embergate summon roll.
#include "Database.h"

namespace Progression
{
int xp_to_next(int level);
int rank_xp_to_next(int rank);
Json unit_stats(const Json& char_def, int level);                 // {hp, atk, def, rec, spd}
Json add_unit_xp(Json& unit_state, int amount);                     // [{level, gains}]
int train_cost(const Json& unit_state);
Json enemy_stats(const Json& enemy_def, int level, double hp_scale = 1.0);
int enemy_xp(const Json& enemy_def, int level);
Json roll_enemy_loot(const Json& enemy_def, int level, Rng& rng);  // {gold, items}
Json resolve_table(const Json& table);
Json roll_table(const Json& table, Rng& rng);                       // {item: qty}
std::vector<std::string> table_items(const Json& table);
int item_xp(const std::string& item_id, const Json& char_def);
int training_gold(int xp);
int xp_to_cap(const Json& unit_state);
int burst_level_for_xp(int xp);
int burst_xp_for_level(int level);
Json scaled_burst(const Json& skill, int level);
double burst_cost(const Json& skill, int level);
std::string burst_level_text(const Json& skill);
int unit_power(const Json& unit_state);
}  // namespace Progression

namespace SummonSystem
{
Json rates(const Json& banner);           // {"3": p, ...} normalised
Json pool_by_rarity(const Json& banner);  // {"3": [ids], ...}
Json hero_rates(const Json& banner);      // {id: p}
std::string roll(const Json& banner, Rng& rng);
}  // namespace SummonSystem
