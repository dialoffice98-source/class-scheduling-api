"""
Class Scheduling Optimization Module
Uses OR-Tools CP-SAT solver to optimize class scheduling with multiple constraints.
"""
from ortools.sat.python import cp_model
from itertools import combinations, product

class SchedulingModel:
    """
    Class scheduling optimization model using OR-Tools.
    
    Refer to formulation in documentation for details.
    """
    
    def __init__(self, sets, params, 
                 allow_unscheduled_classes=False, 
                 quick_scheduling=False, 
                 verbose=0):
        """
        Initialize the scheduling model.
        
        Args:
            sets: Dictionary containing course, faculty, pair, room, day, time sets
            params: Dictionary containing class_details, room_capacity, penalty
            verbose: 0; silent, 1; normal, 2; detailed logging
        """
        ### sets
        self.verbose = verbose

        self.course_set = sets['courses']
        self.faculty_set = sets['faculties']
        self.pair_set = sets['pairs']
        self.room_set = sets['rooms']
        self.room_name = sets['room_names'] #Additional info for self.room_set
        self.day_set = sets['days']
        self.time_set = sets['times']
        
        # pair mapping
        self.course_faculties = sets['course_faculties']
        self.faculty_courses = sets['faculty_courses']
        
        ### params
        self.class_details = params['class_details']
        self.room_capacity = params['room_capacity']
        
        self.penalty = params['penalty']

        # Flags for optional features
        self.with_preferences = False
        self.with_unavailability = False
        self.with_compulsory_course = False
        self.allow_unscheduled_classes = allow_unscheduled_classes
        self.quick_scheduling = quick_scheduling
        
        # Initialize solver
        self.solver = cp_model.CpModel()
        self.scale = 1_000_000
        self.optimization_settings = params['optimization_settings']
        
        # Decision variables
        self.x = {}  # Start time variables
        self.y = {}  # Activity variables
        self.z = {}  # Room setup variables
        self.k = None  # Faculty maximum workload variables
        
        # Solution status
        self.status = None
        self.solution = None
        
    def add_preferences(self, faculty_preferences):
        """
        Add lecturer preferences to the model.
        
        Args:
            faculty_preferences: DataFrame with lecturer preferences (DosenID, Day, Time)
        """
        if self.verbose:
            print("\n  Adding lecturer preferences to the model...")
        self.with_preferences = True
        self.lecturer_preferences = {}
        for lecturer in self.faculty_set:
            for day in self.day_set:
                for time in self.time_set:
                    self.lecturer_preferences[lecturer, day, time] = 0
        for lecturer in faculty_preferences.keys():
            for day in list(faculty_preferences[lecturer].keys())[1:]:
                for time in faculty_preferences[lecturer][day]:
                    self.lecturer_preferences[lecturer, day, time] = 1
        if self.verbose:
            print("  Lecturer preferences added successfully")
    
    def add_unavailability(self, faculty_unavailability):
        """
        Add lecturer unavailability to the model.
        
        Args:
            faculty_unavailability: DataFrame with lecturer unavailability (DosenID, Day, Time)
        """
        if self.verbose:
            print("\n  Adding lecturer unavailability constraints...")
        self.with_unavailability = True
        self.lecturer_unavailability = {}

        for lecturer in self.faculty_set:
            for day in self.day_set:
                for time in self.time_set:
                    self.lecturer_unavailability[lecturer, day, time] = 0

        for lecturer in faculty_unavailability.keys():
            for day in list(faculty_unavailability[lecturer].keys())[1:]:
                for time in faculty_unavailability[lecturer][day]:
                    self.lecturer_unavailability[lecturer, day, time] = 1
        if self.verbose:
            print("  Lecturer unavailability added successfully")

    def add_compulsory_courses(self, compulsory_course):
        """
        Add compulsory course constraints to the model.   
        Args:
            compulsory_course: Dict of compulsory course data from all course
        """
        if self.verbose:
            print("\n  Adding compulsory course constraints...")
        self.with_compulsory_course = True
        self.compulsory_course = compulsory_course
        if self.verbose:
            print("  Compulsory course constraints added successfully")

    
    def create_variables(self):
        """Create decision variables for the model."""
        if self.verbose:
            print("\n  Creating decision variables...")
        # x[p, r, h, t]: Start time variable - class p starts at room r, day h, time t
        for pair in self.pair_set:
            for room in self.room_set:
                for day in self.day_set:
                    for time in self.time_set:
                        self.x[pair, room, day, time] = self.solver.NewBoolVar(
                            f'x_{pair}_{room}_{day}_{time}'
                        )
                        self.y[pair, room, day, time] = self.solver.NewBoolVar(
                            f'y_{pair}_{room}_{day}_{time}'
                        )
        
        # z[r]: Room setup variable - room r is used
        for room in self.room_set:
            self.z[room] = self.solver.NewBoolVar(f'z_{room}')
        
        # k: Faculty maximum workload
        self.k = self.solver.NewIntVar(0, len(self.time_set), 'k')
        
        if self.verbose:
            print("  Decision variables created successfully")
    
    def add_constraints(self):
        """Add all constraints to the model."""
        if self.verbose:
            print("\n  Adding constraints...")
        
        for pair in self.pair_set:
            # Constraint 1: Each class pair can start at most once
            if self.allow_unscheduled_classes:
                self.solver.Add(
                    sum([self.x[pair, room, day, time] 
                         for room in self.room_set 
                         for day in self.day_set 
                         for time in self.time_set]) <= 1   # <= 1 to allow unscheduled classes
                )
            else:
                self.solver.Add(
                    sum([self.x[pair, room, day, time] 
                        for room in self.room_set 
                        for day in self.day_set 
                        for time in self.time_set]) == 1   # == 1 to force all classes to be scheduled
                )
            
            # Constraint 2: Duration - total activity slots = duration * scheduled
            course_id, class_id, session = pair[0], pair[2], pair[3]
            duration = self.class_details[course_id][class_id][session]['duration']
            scheduled = sum([self.x[pair, room, day, time] 
                            for room in self.room_set 
                            for day in self.day_set 
                            for time in self.time_set])
            self.solver.Add(
                sum([self.y[pair, room, day, time] 
                     for room in self.room_set 
                     for day in self.day_set 
                     for time in self.time_set]) == duration * scheduled
            )
        
        for pair in self.pair_set:
            for room in self.room_set:
                for day in self.day_set:
                    # Constraint 3-1: Class activation
                    self.solver.Add(self.x[pair, room, day, 0] >= self.y[pair, room, day, 0])
                    
                    # Constraint 3-2: Class activation
                    for time in range(len(self.time_set) - 1):
                        self.solver.Add(
                            self.x[pair, room, day, time + 1] >= 
                            self.y[pair, room, day, time + 1] - self.y[pair, room, day, time]
                        )
                    
                    # Constraint 4: Sequential activity
                    for time in range(len(self.time_set) - 2):
                        self.solver.Add(
                            self.y[pair, room, day, time] + self.y[pair, room, day, time + 2] <= 
                            1 + self.y[pair, room, day, time + 1]
                        )
        
        # Constraint 5: Class size <= room capacity
        for pair in self.pair_set:
            course_id, class_id, session = pair[0], pair[2], pair[3]
            class_size = self.class_details[course_id][class_id][session]['size']
            for room in self.room_set:
                capacity = self.room_capacity[room]
                for day in self.day_set:
                    for time in self.time_set:
                        self.solver.Add(class_size*self.x[pair, room, day, time] <= capacity)
        
        # Constraint 6: No lecturer conflicts
        for faculty in self.faculty_set:
            for day in self.day_set:
                for time in self.time_set:
                    lecturer_pairs = [pair for pair in self.pair_set if pair[1] == faculty]
                    self.solver.Add(
                        sum([self.y[pair, room, day, time] 
                             for pair in lecturer_pairs 
                             for room in self.room_set]) <= 1
                    )
        
        # Constraint 7: No room conflicts
        for room in self.room_set:
            for day in self.day_set:
                for time in self.time_set:
                    self.solver.Add(
                        sum([self.y[pair, room, day, time] 
                             for pair in self.pair_set]) <= 1
                    )

        # Constraint 8: Room setup activation
        for room in self.room_set:
            for pair in self.pair_set:
                for day in self.day_set:
                    for time in self.time_set:
                        self.solver.Add(self.z[room] >= self.x[pair, room, day, time])

        # Constraint 9: Lecturer's daily workload
        for faculty in self.faculty_set:
            for day in self.day_set:
                workload = sum(self.y[pair, room, day, time]
                               for pair in self.pair_set if pair[1] == faculty
                               for room in self.room_set
                               for time in self.time_set)
                self.solver.Add(self.k >= workload)
        
        # Constraint 10: Lecturer's unavailability
        if self.with_unavailability:
            for pair in self.pair_set:
                for room in self.room_set:
                    for day in self.day_set:
                        for time in self.time_set:
                            self.solver.Add(
                                self.y[pair, room, day, time] <= 1 - self.lecturer_unavailability[pair[1], day, time]
                            )
        
        # Constraint 11: Sessions of the same course/class should not be scheduled in the same day
        for course_id in self.course_set:
            for class_id in self.class_details[course_id].keys():
                for room in self.room_set:
                    for day in self.day_set:
                        sessions_list = list(self.class_details[course_id][class_id].keys())
                        if len(sessions_list) > 1:
                            class_dict = self.class_details[course_id][class_id]
                            self.solver.Add(
                                sum(self.x[(course_id, class_dict[session]["lecturer"],
                                           class_id, session),
                                           room, day, time]
                                    for session in sessions_list 
                                    for time in self.time_set) <= 1
                            )

        
        # Constraint 12: Compulsory courses should not overlap in time
        if self.with_compulsory_course:
            for _, package in self.compulsory_course.items():
                for course1, course2 in combinations(package, 2):
                    # Find all pairs for course1 and course2
                    pairs1 = [pair for pair in self.pair_set if pair[0] == course1]
                    pairs2 = [pair for pair in self.pair_set if pair[0] == course2]
                    # For each combination of pair from course 1 and course 2
                    for pair1, pair2 in product(pairs1, pairs2):
                        for day in self.day_set:
                            for time in self.time_set:
                                y1 = sum([self.y[pair1, room, day, time] for room in self.room_set])
                                y2 = sum([self.y[pair2, room, day, time] for room in self.room_set])
                                self.solver.Add(y1 + y2 <= 1)
                                
        if self.verbose:    
            print("  All constraints added successfully")
    
    def set_objective(self):
        """
        Set the objective function.
        
        Args:
            w1: Weight for minimizing empty room slots
            w2: Weight for minimizing room usage
            w3: Weight for minimizing maximum faculty workload
            w4: Weight for minimizing lecturer preferences violations
        """
        if self.verbose:
            print("\n  Setting objective function...")
        SCALE = self.scale  # Use instance scale

        objective_terms = []
        
        w1 = int(self.penalty['utilisasi_ruangan'])
        w2 = int(self.penalty['jumlah_ruangan'])
        w3 = int(self.penalty['maks_jam_mengajar'])
        
        # Objective 1: Minimize room capacity mismatch
        objective_terms.append(w1* SCALE * len(self.pair_set))
        for pair in self.pair_set:
            class_size = self.class_details[pair[0]][pair[2]][pair[3]]['size']
            for room in self.room_set:
                capacity = self.room_capacity[room]
                coef = -int(w1 * SCALE * class_size / capacity)
                for day in self.day_set:
                    for time in self.time_set:
                        objective_terms.append(coef * self.x[pair, room, day, time])
        
        # Objective 2: Minimize total room usage
        for room in self.room_set:
            objective_terms.append(w2 * SCALE * self.z[room])
        
        # Objective 3: Minimize maximum faculty workload
        objective_terms.append(w3 * SCALE * self.k)
        
        # Optional Objective 4: Minimize lecturer preferences violations
        if self.with_preferences:
            w4 = int(self.penalty['preferensi_dosen'])
            
            # Calculate total duration of all classes
            total_duration = sum(
                self.class_details[pair[0]][pair[2]][pair[3]]['duration']
                for pair in self.pair_set
            )
            objective_terms.append(w4 * SCALE * total_duration)
            
            # Subtract preferred slots that are used
            for pair in self.pair_set:
                for room in self.room_set:
                    for day in self.day_set:
                        for time in self.time_set:
                            pref = self.lecturer_preferences[pair[1], day, time]
                            coef = -w4 * SCALE * pref 
                            objective_terms.append(coef * self.y[pair, room, day, time])
        self.solver.Minimize(sum(objective_terms))
        
        if self.verbose:
            print("  Objective function set successfully")

    def build(self):
        """
        Model building
        """
        if self.verbose:
            print("\n  Building the model...")

        self.create_variables()
        self.add_constraints()
        self.set_objective()
        if self.verbose:
            print("  Model built successfully")
    
    def solve(self):
        """Solve the optimization model and return decision variables + status."""
        if self.verbose:
            print("\n  Solving the model...")
        solver = cp_model.CpSolver()
        solver.parameters.random_seed = 42  # Deterministic behavior

        # Limit CP-SAT to 4 threads
        solver.parameters.num_search_workers = self.optimization_settings['num_search_workers']
        
        if self.verbose == 2:
            solver.parameters.log_search_progress = True  # Monitor detailed progress

        # Solver Settings
        solver.parameters.linearization_level = self.optimization_settings['linearization_level']  # More aggressive linearization
        solver.parameters.symmetry_level = self.optimization_settings['symmetry_level']  # Break symmetries in schedules

        if self.quick_scheduling:
            solver.parameters.relative_gap_limit = self.optimization_settings['relative_gap_limit']  # 0.5% gap
            solver.parameters.max_time_in_seconds = self.optimization_settings['max_time_mins']*60  # 10 minute time limit
            #solver.parameters.num_conflicts_limit = 10000  # Limit conflicts to speed up

        status_code = solver.Solve(self.solver)
        
        # Map status code to readable string
        if status_code == cp_model.OPTIMAL:
            self.status = "OPTIMAL"
        elif status_code == cp_model.FEASIBLE:
            self.status = "FEASIBLE"
        elif status_code == cp_model.INFEASIBLE:
            self.status = "INFEASIBLE"
        elif status_code == cp_model.MODEL_INVALID:
            self.status = "MODEL_INVALID"
        else:
            self.status = "UNKNOWN"
        
        # Store solver reference for value extraction
        self._cpsat_solver = solver
        
        # If infeasible → no solution exists
        if self.status in ["INFEASIBLE", "MODEL_INVALID", "UNKNOWN"]:
            self.solution_vars = {}
        else:
            # Extract solution values using CP-SAT solver.Value()
            x_eval = {
                key: solver.Value(var)
                for key, var in self.x.items()
                if solver.Value(var) > 0.5
            }
            
            z_eval = {
                room: solver.Value(var)
                for room, var in self.z.items()
            }
            
            k_eval = solver.Value(self.k)
            
            self.solution_vars = {
                "x": x_eval,
                "z": z_eval,
                "k": k_eval,
                "objective": solver.ObjectiveValue() / self.scale
            }