from Levenshtein import distance as string_distance

def get_system_autocomplete(input_so_far: str, all_systems: list[str]) -> list[str]:
        len_inp = len(input_so_far)+1
        systems_with_dist = map(lambda s: (s, string_distance(s[:len_inp], input_so_far)), all_systems)
        systems_with_dist = filter(lambda sd: sd[1] < 2, systems_with_dist)
        systems_with_dist = sorted(systems_with_dist, key=lambda sd: sd[1])
        
        choices = []
        for system, _ in systems_with_dist[:25]:
            choices.append({"name": system, "value": system})
        return choices