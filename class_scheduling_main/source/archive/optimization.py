"""
Class Scheduling Optimization Module
Uses OR-Tools SCIP solver to optimize class scheduling with multiple constraints.
"""

from ortools.linear_solver import pywraplp

class SchedulingModel:
    """
    Class scheduling optimization model using OR-Tools.
    
    Refer to formulation in documentation for details.
    """
    
    def __init__(self, sets, params,verbose):
        """
        Initialize the scheduling model.
        
        Args:
            course_df: DataFrame with course data (class_id, dosen_id, jumlah_mhs, durasi_jam)
            room_df: DataFrame with room data (ruangan_id, kapasitas)
            day_list: List of days
            num_time_slots: Number of time slots per day
        """
        ### sets
        self.verbose = verbose

        self.course_set = sets['courses']
        self.faculty_set = sets['faculties']
        self.pair_set = sets['pairs']
        self.room_set = sets['rooms']
        self.day_set = sets['days']
        self.time_set = sets['times']
        
        # pair mapping
        self.course_faculties = sets['course_faculties']
        self.faculty_courses = sets['faculty_courses']
        
        ### params
        self.class_details = params['class_details']
        self.room_capacity = params['room_capacity']
        self.penalty = params['penalty']
        self.with_preferences = False
        self.with_unavailability = False
        
        # Initialize solver
        self.solver = pywraplp.Solver.CreateSolver('SCIP')
        
        # Decision variables
        self.x = {}  # Start time variables
        self.y = {}  # Activity variables
        self.z = {}  # Room setup variables
        self.k = None  # Faculty maximum workload variables
        
        # Solution status
        self.status = None
        self.solution = None
        
    def add_preferences(self, lecturers_pref_dict):
        """
        Add lecturer preferences to the model.
        
        Args:
            pref_dosen_df: DataFrame with lecturer preferences (dosen_id, day, time_slot)
        """
        if self.verbose:
            print("Adding lecturer preferences to the model")
        self.with_preferences = True
        self.lecturer_preferences = {}
        for d in self.lecturers_unique:
            for h in self.day_list:
                for t in self.time_slots:
                    if (d, h, t) in lecturers_pref_dict.itertuples(index=False, name=None):
                        self.lecturer_preferences[d, h, t] = 1
                    else:
                        self.lecturer_preferences[d, h, t] = 0
        if self.verbose:
            print("Lecturer preferences added successfully")
    
    def add_unavailability(self, lecturers_unav_dict):
        """
        Add lecturer unavailability to the model.
        
        Args:
            unav_dosen_df: DataFrame with lecturer unavailability (dosen_id, day, time_slot)
        """
        if self.verbose:
            print("Adding lecturer unavailability constraints")
        self.with_unavailability = True
        self.lecturer_unavailability = {}
        for d in self.lecturers_unique:
            for h in self.day_list:
                for t in self.time_slots:
                    if (d, h, t) in lecturers_unav_dict.itertuples(index=False, name=None):
                        self.lecturer_unavailability[d, h, t] = 1
                    else:
                        self.lecturer_unavailability[d, h, t] = 0
        if self.verbose:
            print("Lecturer unavailability constraints added successfully")
    
    def create_variables(self):
        """Create decision variables for the model."""
        if self.verbose:
            print("\nCreating decision variables...")
        # x[p, r, h, t]: Start time variable - class p starts at room r, day h, time t
        for pair in self.pair_set:
            for room in self.room_set:
                for day in self.day_set:
                    for time in self.time_set:
                        self.x[pair, room, day, time] = self.solver.IntVar(
                            0, 1, f'x_{pair}_{room}_{day}_{time}'
                        )
                        
                        self.y[pair, room, day, time] = self.solver.IntVar(
                            0, 1, f'y_{pair}_{room}_{day}_{time}'
                        )
        
        # z[r]: Room setup variable - room r is used
        for room in self.room_set:
            self.z[room] = self.solver.IntVar(0, 1, f'z_{room}')
        
        # k: Facutly maximum workload
        self.k = self.solver.IntVar(0, len(self.time_set), 'k')
        if self.verbose:
            print("Decision variables created successfully")
    
    def add_constraints(self):
        """Add all constraints to the model."""
        if self.verbose:
            print("\nAdding constraints...")
        for pair in self.pair_set:
            # Constraint 1: Each class pair can start at most once
            self.solver.Add(
                self.solver.Sum([self.x[pair, room, day, time] 
                               for room in self.room_set 
                               for day in self.day_set 
                               for time in self.time_set]) <= 1
            )
        
            # Constraint 2: Duration - total activity slots = duration * scheduled
            course_id = pair[0] #pair = (course_id, faculty_id)
            duration = self.class_details[course_id]['duration']
            scheduled = self.solver.Sum([self.x[pair, room, day, time] 
                                        for room in self.room_set 
                                        for day in self.day_set 
                                        for time in self.time_set])
            self.solver.Add(
                self.solver.Sum([self.y[pair, room, day, time] 
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
            course_id = pair[0] #pair = (course_id, faculty_id)
            class_size = self.class_details[course_id]['size']
            for room in self.room_set:
                capacity = self.room_capacity[room]
                for day in self.day_set:
                    for time in self.time_set:
                        self.solver.Add(
                            class_size * self.x[pair, room, day, time] <= capacity
                        )
        
        # Constraint 6: No lecturer conflicts
        for faculty in self.faculty_set:
            for day in self.day_set:
                for time in self.time_set:
                    lecturer_pairs = [pair for pair in self.pair_set if pair[1] == faculty] #pair = (course_id, faculty_id)
                    self.solver.Add(
                        self.solver.Sum([self.y[pair, room, day, time] 
                                       for pair in lecturer_pairs 
                                       for room in self.room_set]) <= 1
                    )
        
        # Constraint 7: No room conflicts
        for room in self.room_set:
            for day in self.day_set:
                for time in self.time_set:
                    self.solver.Add(
                        self.solver.Sum([self.y[pair, room, day, time] 
                                       for pair in self.pair_set]) <= 1
                    )
        
        # Constraint 8: Room setup activation
        for room in self.room_set:
            for pair in self.pair_set:
                for day in self.day_set:
                    for time in self.time_set:
                        self.solver.Add(self.z[room] >= self.x[pair, room, day, time])
        
        #Constraint 9: Lecturer's daily workload
        for faculty in self.faculty_set:
            for day in self.day_set:
                self.solver.Add(self.k >= 
                                self.solver.Sum(self.y[(course, faculty), room, day, time] 
                                                for course in self.faculty_courses[faculty]
                                                for room in self.room_set
                                                for time in self.time_set))
        
        #Constraint 10: Lecturer's unavailability
        if self.with_unavailability:
            #print("Adding lecturer unavailability constraints")
            for p in self.pairs:
                    for r in self.rooms:
                        for h in self.day_list:
                            for t in self.time_slots:
                                self.solver.Add(self.y[p,r,h,t] <= 1- self.lecturer_unavailability[p[1],h,t])
        if self.verbose:    
            print("All constraints added successfully")
    
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
            print("\nSetting objective function...")
        # Objective 1: Minimize room capacity mismatch
        obj1 = self.solver.Sum([
            (1 - self.class_details[pair[0]]['size'] / self.room_capacity[room]* self.x[pair, room, day, time]) 
            for pair in self.pair_set
            for room in self.room_set
            for day in self.day_set
            for time in self.time_set
        ])
        
        # Objective 2: Minimize total room usage
        obj2 = self.solver.Sum([self.z[room] for room in self.room_set])
        
        # Objective 3: Minimize maximum faculty workload
        obj3 = self.k
        
        # Combined objective (weighted sum)
        w1 = self.penalty['utilisasi_ruangan']
        w2 = self.penalty['jumlah_ruangan']
        w3 = self.penalty['maks_jam_mengajar']

        # Optional Objective
        # Objective 4: Minimize lecturer preferences violations
        if self.with_preferences:
            obj4 = self.solver.Sum([
                (1 - self.lecturer_preferences[pair[1], day, time]) * self.y[pair, room, day, time]
                for pair in self.pair_set
                for room in self.room_set
                for day in self.day_set
                for time in self.time_set
            ])
            w4 = self.penalty['preferensi_dosen']
        else:
            obj4=0
            w4=0

        self.solver.Minimize(w1 * obj1 + w2 * obj2 + w3 * obj3 + w4 * obj4)
        if self.verbose:
            print("Objective function set successfully")

    def build(self):
        """
        Model building
        """
        if self.verbose:
            print("\nBuilding the model...")

        self.create_variables()
        self.add_constraints()
        self.set_objective()
        if self.verbose:
            print("Model built successfully")
    
    def solve(self):
        def _eval_vars(self, var_dict):
            """Return only variables with value > 0.5 as {key: value}."""
            return {key: var.solution_value()
                    for key, var in var_dict.items()
                    if var.solution_value() > 0.5}
        
        """Solve the optimization model and return decision variables + status."""
        if self.verbose:
            print("\nSolving the model...")
            
        status_code = self.solver.Solve()
        
        # Map status code to readable string
        if status_code == pywraplp.Solver.OPTIMAL:
            self.status = "OPTIMAL"
        elif status_code == pywraplp.Solver.FEASIBLE:
            self.status = "FEASIBLE"
        elif status_code == pywraplp.Solver.INFEASIBLE:
            self.status = "INFEASIBLE"
        elif status_code == pywraplp.Solver.UNBOUNDED:
            self.status = "UNBOUNDED"
        else:
            self.status = "UNKNOWN"
        
        # If infeasible or unbounded → no solution exists
        if self.status in ["INFEASIBLE", "UNBOUNDED", "UNKNOWN"]:
            self.solution_vars = {}
        else:
            # Otherwise return raw OR-Tools variable objects
            x_eval = {
                key: var.solution_value()
                for key, var in self.x.items()
                if var.solution_value() > 0.5     # only show active ones
            }
            
            z_eval = {
                room: var.solution_value()
                for room, var in self.z.items()
            }
            
            k_eval = self.k.solution_value()
            
            self.solution_vars = {
                "x": x_eval,
                "z": z_eval,
                "k": k_eval
            }