import time as timer
import heapq
import random
from single_agent_planner import compute_heuristics, a_star, get_location, get_sum_of_cost


def detect_collision(path1, path2):
    ##############################
    # Task 3.1: Return the first collision that occurs between two robot paths (or None if there is no collision)
    #           There are two types of collisions: vertex collision and edge collision.
    #           A vertex collision occurs if both robots occupy the same location at the same timestep
    #           An edge collision occurs if the robots swap their location at the same timestep.
    #           You should use "get_location(path, t)" to get the location of a robot at time t.

    pair_loc1 = [None] * 2
    pair_loc2 = [None] * 2
    for ts in range(20):

        pair_loc1[0] = get_location(path1, ts)
        pair_loc1[1] = get_location(path1, ts + 1)

        pair_loc2[0] = get_location(path2, ts)
        pair_loc2[1] = get_location(path2, ts + 1)

        # vertex collisions
        if pair_loc1[0] == pair_loc2[0]:
            vertex_collision = { 'ts': ts, 'loc': [pair_loc1[0]] } 
            return vertex_collision

        # edge collisions
        if (pair_loc1[0] == pair_loc2[0] and pair_loc1[1] == pair_loc2[1]) or (pair_loc1[0] == pair_loc2[1] and pair_loc1[1] == pair_loc2[0]):
            edge_collision = { 'ts': ts + 1, 'loc': pair_loc1 }
            return edge_collision

    return None


def detect_collisions(paths):
    ##############################
    # Task 3.1: Return a list of first collisions between all robot pairs.
    #           A collision can be represented as dictionary that contains the id of the two robots, the vertex or edge
    #           causing the collision, and the timestep at which the collision occurred.
    #           You should use your detect_collision function to find a collision between two robots.

    agents_list = []
    for i in range (len(paths)):
        agents_list.append(i)

    # https://www.geeksforgeeks.org/python-all-possible-pairs-in-list/
    pairs_list = [(a, b) for idx, a in enumerate(paths) for b in paths[idx + 1:]]
    agents = [(a, b) for idx, a in enumerate(agents_list) for b in agents_list[idx + 1:]]

    first_collisions = []

    for i in range(len(pairs_list)):
        a = detect_collision(pairs_list[i][0], pairs_list[i][1])

        if a:
            collision = { 'a1': agents[i][0], 'a2': agents[i][1], 'loc': a['loc'], 'timestep': a['ts'] }
            first_collisions.append(collision)

    return first_collisions


def standard_splitting(collision):
    ##############################
    # Task 3.2: Return a list of (two) constraints to resolve the given collision
    #           Vertex collision: the first constraint prevents the first agent to be at the specified location at the
    #                            specified timestep, and the second constraint prevents the second agent to be at the
    #                            specified location at the specified timestep.
    #           Edge collision: the first constraint prevents the first agent to traverse the specified edge at the
    #                          specified timestep, and the second constraint prevents the second agent to traverse the
    #                          specified edge at the specified timestep

    # edge constraint
    if len(collision['loc']) > 1:
        constraint_1 = { 'agent': collision['a1'], 'loc': collision['loc'], 'timestep': collision['timestep'], 'positive': False }
        constraint_2 = { 'agent': collision['a2'], 'loc': collision['loc'], 'timestep': collision['timestep'], 'positive': False }
        new_constraints = [constraint_1, constraint_2]

    # vertex constraint
    else:
        constraint_1 = { 'agent': collision['a1'], 'loc': collision['loc'], 'timestep': collision['timestep'], 'positive': False }
        constraint_2 = { 'agent': collision['a2'], 'loc': collision['loc'], 'timestep': collision['timestep'], 'positive': False }
        new_constraints = [constraint_1, constraint_2]

    return new_constraints


def disjoint_splitting(collision):
    ##############################
    # Task 4.1: Return a list of (two) constraints to resolve the given collision
    #           Vertex collision: the first constraint enforces one agent to be at the specified location at the
    #                            specified timestep, and the second constraint prevents the same agent to be at the
    #                            same location at the timestep.
    #           Edge collision: the first constraint enforces one agent to traverse the specified edge at the
    #                          specified timestep, and the second constraint prevents the same agent to traverse the
    #                          specified edge at the specified timestep
    #           Choose the agent randomly

    rand_agent = random.randint(0, 1)
    other_agent = 1 if rand_agent == 0 else 0

    # edge constraint
    if len(collision['loc']) > 1:
        constraint_1 = { 'agent': rand_agent, 'loc': collision['loc'], 'timestep': collision['timestep'], 'positive': True }
        constraint_2 = { 'agent': other_agent, 'loc': collision['loc'], 'timestep': collision['timestep'], 'positive': False}
        new_constraints = [constraint_1, constraint_2]

    # vertex constraint
    else:
        constraint_1 = { 'agent': rand_agent, 'loc': collision['loc'], 'timestep': collision['timestep'], 'positive': True }
        constraint_2 = { 'agent': other_agent, 'loc': collision['loc'], 'timestep': collision['timestep'], 'positive': False }
        new_constraints = [constraint_1, constraint_2]

    return new_constraints


def paths_violate_constraint(constraint, paths):
    assert constraint['positive'] is True
    rst = []
    for i in range(len(paths)):
        if i == constraint['agent']:
            continue
        curr = get_location(paths[i], constraint['timestep'])
        prev = get_location(paths[i], constraint['timestep'] - 1)
        if len(constraint['loc']) == 1:  # vertex constraint
            if constraint['loc'][0] == curr:
                rst.append(i)
        else:  # edge constraint
            if constraint['loc'][0] == prev or constraint['loc'][1] == curr \
                    or constraint['loc'] == [curr, prev]:
                rst.append(i)
    return rst


class CBSSolver(object):
    """The high-level search of CBS."""

    def __init__(self, my_map, starts, goals):
        """my_map   - list of lists specifying obstacle positions
        starts      - [(x1, y1), (x2, y2), ...] list of start locations
        goals       - [(x1, y1), (x2, y2), ...] list of goal locations
        """

        self.my_map = my_map
        self.starts = starts
        self.goals = goals
        self.num_of_agents = len(goals)

        self.num_of_generated = 0
        self.num_of_expanded = 0
        self.CPU_time = 0

        self.open_list = []

        # compute heuristics for the low-level search
        self.heuristics = []
        for goal in self.goals:
            self.heuristics.append(compute_heuristics(my_map, goal))

    def push_node(self, node):
        heapq.heappush(self.open_list, (node['cost'], len(node['collisions']), self.num_of_generated, node))
        print("Generate node {}".format(self.num_of_generated))
        self.num_of_generated += 1

    def pop_node(self):
        _, _, id, node = heapq.heappop(self.open_list)
        print("Expand node {}".format(id))
        self.num_of_expanded += 1
        return node

    def remove_goal_duplicates(self, path):
        for i in range(len(path)):
            while path[i][-1] == path[i][-2]:
                if len(path[i]) == 2:
                    break
                path[i].pop(-2)

        return path

    def find_solution(self, disjoint=True):
        """ Finds paths for all agents from their start locations to their goal locations

        disjoint    - use disjoint splitting or not
        """

        self.start_time = timer.time()

        # Generate the root node
        # constraints   - list of constraints
        # paths         - list of paths, one for each agent
        #               [[(x11, y11), (x12, y12), ...], [(x21, y21), (x22, y22), ...], ...]
        # collisions     - list of collisions in paths
        root = {'cost': 0,
                'constraints': [],
                'paths': [],
                'collisions': []}
        for i in range(self.num_of_agents):  # Find initial path for each agent
            path = a_star(self.my_map, self.starts[i], self.goals[i], self.heuristics[i],
                          i, root['constraints'])
            if path is None:
                raise BaseException('No solutions')
            root['paths'].append(path)

        root['cost'] = get_sum_of_cost(root['paths'])
        root['collisions'] = detect_collisions(root['paths'])
        self.push_node(root)

        # Task 3.1: Testing
        print("root[collisions] = ", str(root['collisions']))

        # Task 3.2: Testing
        for collision in root['collisions']:
            print("root[collisions]: ", str(standard_splitting(collision)))

        ##############################
        # Task 3.3: High-Level Search
        #           Repeat the following as long as the open list is not empty:
        #             1. Get the next node from the open list (you can use self.pop_node()
        #             2. If this node has no collision, return solution
        #             3. Otherwise, choose the first collision and convert to a list of constraints (using your
        #                standard_splitting function). Add a new child node to your open list for each constraint
        #           Ensure to create a copy of any objects that your child nodes might inherit

        while len(self.open_list) > 0:
            P = self.pop_node()
            
            # P is a goal node
            if not P['collisions']:
                wee = self.remove_goal_duplicates(P['paths'])
                P['paths'] = wee
                self.print_results(P)
                return P['paths']
            
            # pick first collision in P.collisions
            collision = P['collisions'][0]

            if disjoint:
                constraints = disjoint_splitting(collision)
            else:
                constraints = standard_splitting(collision)

            # for each constraint
            for constraint in constraints:
                new_constraint_set = P['constraints'].copy()      # previous constraints
                new_constraint_set.append(constraint)             # add the new constraint

                Q = {'cost': 0,
                     'constraints': new_constraint_set,
                     'paths': P['paths'],
                     'collisions': []}
                    
                a = constraint['agent']

                update = True

                if constraint['positive'] == False:
                    path = a_star(self.my_map, self.starts[a], self.goals[a], self.heuristics[a], a, Q['constraints'])

                    if path:

                        new_path_set = P['paths'].copy()
                        new_path_set[a] = path

                        # Q['paths'] = new_path_set
                        # Q['collisions'] = detect_collisions(Q['paths'])
                        # Q['cost'] = get_sum_of_cost(Q['paths'])
                        # self.push_node(Q)

                else:

                    agent_ids = paths_violate_constraint(constraint, P['paths'])
                    agent_ids.append(a)

                    for i in range(len(agent_ids)):
                        path = a_star(self.my_map, self.starts[i], self.goals[i], self.heuristics[i], i, Q['constraints'])

                        if path == None:
                            update = False

                        # update all paths
                        new_path_set = P['paths'].copy()
                        new_path_set[i] = path

                Q['paths'] = new_path_set
                Q['collisions'] = detect_collisions(Q['paths'])
                Q['cost'] = get_sum_of_cost(Q['paths'])

                if update == True:
                    self.push_node(Q)


                # if the constraint is negative
                # add this constraint on top of the old set of constraints
                # find the agent corresponding to this constraint
                # find a new path for this agent with the new set of constraints


                # if the constraint is positive
                # add this constraint on top of the old sete of constraints
                # find the agent corresponding to this constraint and find all agents that violate the constraint
                # find a new path for all these agent with the new set of constraints

        return None


    def print_results(self, node):
        print("\n Found a solution! \n")
        CPU_time = timer.time() - self.start_time
        print("CPU time (s):    {:.2f}".format(CPU_time))
        print("Sum of costs:    {}".format(get_sum_of_cost(node['paths'])))
        print("Expanded nodes:  {}".format(self.num_of_expanded))
        print("Generated nodes: {}".format(self.num_of_generated))
