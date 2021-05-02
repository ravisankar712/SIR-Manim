from manimlib.imports import *

COLOR_MAP = {
    "S" : "#fac661",
    "I" : RED,
    "R" : "#35df90",
    "D" : BLACK,
    "V" : "#33a9ff"
}

def update_time(m, dt):
    m.time += dt

class City(VGroup):
    CONFIG = {
        "size" : 7,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.time = 0.0
        self.add_body()
        self.people = VGroup()

        self.add_updater(update_time)
    
    def add_body(self):
        city = Square()
        city.set_height(self.size)
        city.set_stroke(WHITE, 3.0)
        self.body = city
        self.add(self.body)

DEFAULT_CITY = City(size=10)

class Person(VGroup):
    CONFIG = { 
        "size" : 0.2,
        "max_speed" : 1,
        "wall_buff" : 1.0,
        "random_walk_interval" : 1.0,
        "step_size" : 1.5,
        "gravity_strength" : 1.0,
        "infection_ring_style" : {
            "stroke_color" : RED,
            "stroke_opacity" : 1,
            "stroke_width" : 1.0
        },
        "infection_ring_anim_time" : 0.6,
        "infection_radius" : 0.3,
        "infection_prob" : 0.8,
        "infection_time" : 5,
        "social_distance_factor" : 0.0,
        "obey_social_distancing" : True
    }

    def __init__(self, city=DEFAULT_CITY, **kwargs):
        super().__init__(**kwargs)

        self.status = "S"
        self.time = 0.0
        self.last_step_update = -1.0
        self.infected_time = -np.inf
        self.recovered_time = -np.inf
        self.gravity_center = None
        self.isUpdating = True
        self.velocity = np.zeros(3)
        self.city = city

        self.add_body()
        self.add_infection_ring()

        #updaters 
        self.add_updater(update_time)
        self.add_updater(lambda m, dt : m.update_position(dt))
        self.add_updater(lambda m, dt : m.update_infection_ring(dt))
        self.add_updater(lambda m, dt : m.update_color(dt))
        self.add_updater(lambda m, dt : m.update_status(dt))

    def add_infection_ring(self):
        ring = Circle(radius=self.size/2.5)
        ring.set_style(**self.infection_ring_style)
        ring.move_to(self.get_center())
        self.add_to_back(ring)
        self.infection_ring = ring

    def add_body(self):
        body = self.get_body()
        body.set_height(self.size)
        body.set_color(COLOR_MAP[self.status])
        body.move_to(self.get_center())
        self.body = body
        self.add(self.body)

    def get_body(self):
        return Dot()

    def set_status(self, status):
        self.status = status
        if status == "I":
            self.infected_time = self.time
        elif status == "R":
            self.recovered_time = self.time

    def pause_updation(self):
        self.isUpdating = False
    
    def resume_updation(self):
        self.isUpdating = True

    def change_city(self, city):
        self.city = city

    def update_position(self, dt):
        if self.isUpdating:
            c = self.get_center()
            total_force = np.zeros(3)

            #updating gravity center
            if (self.time - self.last_step_update) >= self.random_walk_interval:
                self.last_step_update = self.time
                random_vec = rotate_vector(RIGHT, TAU * random.random())
                self.gravity_center = c + random_vec * self.step_size
            
            #gravity
            if self.gravity_center is not None:
                f = self.gravity_center - c
                r = np.linalg.norm(f)
                if r > 0.0:
                    total_force += f/r**2 * self.gravity_strength


            #walls
            dl = self.city.get_corner(DL)
            ur = self.city.get_corner(UR)
            wall_force = np.zeros(3)

            for i in range(2):
                to_dl = c[i] - dl[i] - self.size/2.0
                to_ur = ur[i] - c[i] - self.size/2.0

                if to_dl < 0.0:
                    self.velocity[i] *= -1
                    self.set_coord(dl[i] + self.size/2.0, i)
                
                if to_ur < 0.0:
                    self.velocity[i] *= -1
                    self.set_coord(ur[i] - self.size/2.0, i)
                
                #dl force should be +ve, the other -ve
                wall_force[i] += max(0, (1.0/to_dl - 1.0/self.wall_buff))
                wall_force[i] -= max(0, (1.0/to_ur - 1.0/self.wall_buff))
            
            total_force += wall_force

            #social distancing
            if self.social_distance_factor > 0.0 and self.obey_social_distancing:
                people = self.city.people
                repulsion_force = np.zeros(3)
                for other in people:
                    if other != self:
                        vec = self.get_center() - other.get_center()
                        d = np.linalg.norm(vec)
                        if d > 0.0:
                            repulsion_force += vec/d**3 * self.social_distance_factor
                total_force += repulsion_force

            #update velocity
            self.velocity += total_force * dt

            #limit speed
            speed = np.linalg.norm(self.velocity)
            if speed > self.max_speed:
                self.velocity = self.max_speed * self.velocity / speed

            #update postion
            self.shift(self.velocity * dt)

    def update_infection_ring(self, dt):
        if self.status == "I":
            if self.time - self.infected_time <= self.infection_ring_anim_time:
                alpha = (self.time - self.infected_time)/self.infection_ring_anim_time
                if 0.0 <= alpha <= 1.0:
                    self.infection_ring.set_width(alpha * self.size * 3 + (1.0-alpha)*self.size)
                    self.infection_ring.set_style(stroke_opacity=1.0 - alpha, stroke_width=alpha*5)
            else:
                self.infection_ring.set_style(stroke_opacity=0.0, stroke_width=0.0)
        
    def update_color(self, dt):
        if self.status == "I":
            if self.time - self.infected_time <= self.infection_ring_anim_time:
                alpha = (self.time - self.infected_time)/self.infection_ring_anim_time
                if 0.0 <= alpha <= 1.0:
                    self.body.set_color(interpolate_color(COLOR_MAP["S"], COLOR_MAP["I"], alpha))

        if self.status == "R":
            if self.time - self.recovered_time <= self.infection_ring_anim_time:
                alpha = (self.time - self.recovered_time)/self.infection_ring_anim_time
                if 0.0 <= alpha <= 1.0:
                    self.body.set_color(interpolate_color(COLOR_MAP["I"], COLOR_MAP["R"], alpha))

    def update_status(self, dt):
        people = self.city.people
        infected_people = list(filter(lambda m : m.status == "I", people))

        if self.status == "S":
            for other in infected_people:
                if other != self:
                        d = np.linalg.norm(self.get_center() - other.get_center())
                        if d < self.infection_radius and random.random() < self.infection_prob:
                            self.set_status("I")
        elif self.status == "I":
            if (self.time - self.infected_time) > self.infection_time:
                    self.set_status("R")


class SIRSimulation(VGroup):
    CONFIG = {
        "n_cities" : 1,
        "city_size" : 7,
        "n_citizen_per_city" : 50,
        "social_distance_obedience" : 0.0, #anything between 0 and 1
        "person_config" : {
            "infection_prob" : 0.5,
            "social_distance_factor" : 0.2,
        },
        "interstate_travel_prob" : 1.0,
        "interstate_travel_time" : 0.5,
        "interstate_travel_freq" : 1.0
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.time = 0.0
        self.last_travel_time = -np.inf
        self.add_cities()
        self.add_people()
        self.infect_one_person()

        self.add_updater(update_time)

    def add_cities(self):
        self.cities = VGroup()
        for _ in range(self.n_cities):
            city = City(size=self.city_size)
            self.cities.add(city)

        self.cities.arrange_in_grid(buff=LARGE_BUFF)
        self.add(self.cities)

    def add_people(self):
        self.people = VGroup()
        for city in self.cities:
            for _ in range(self.n_citizen_per_city):
                if random.random() < self.social_distance_obedience:
                    obey_social_distancing = True
                else:
                    obey_social_distancing = False
                p = Person(city=city, **self.person_config, obey_social_distancing=obey_social_distancing)

                dl = city.get_corner(DL)
                ur = city.get_corner(UR)
                x = random.uniform(dl[0], ur[0])
                y = random.uniform(dl[1], ur[1])
                p.move_to(np.array([x, y, 0.0]))
                self.people.add(p)
                city.people.add(p)

        self.add(self.people)
    
    def infect_one_person(self):
        p = random.choice(self.people)
        p.set_status("I")


class SimulationTemplate(ZoomedScene):
    CONFIG = {
        "simulation_config" : {
            "n_cities" : 1,
            "city_size" : 7,
            "n_citizen_per_city" : 50,
            "infection_prob" : 0.5,
            "social_distance_obedience" : 0.0, #anything between 0 and 1
            "person_config" : {
                "infection_prob" : 0.5,
                "social_distance_factor" : 0.2,
            }
        }
    }

    def setup(self):
        super().setup()
        self.add_simulation()
        self.position_camera()

    def add_simulation(self):
        self.simulation = SIRSimulation(**self.simulation_config)
        self.add(self.simulation)

    def position_camera(self):
        cities = self.simulation.cities
        frame = self.camera_frame
        height = cities.get_height() + 1
        width = cities.get_width() * 2

        if frame.get_height() < height:
            frame.set_height(height)
        if frame.get_width() < width:
            frame.set_width(width)
        
        frame.next_to(cities.get_right(), LEFT, buff=-0.05*cities.get_width())


    def construct(self):
        self.wait_until(self.count)
        self.wait(5)
    
    def count(self):
        c = 0
        for p in self.simulation.people:
            if p.status == "I":
                c += 1
        return (c == 0)




class Test(Scene):
    def construct(self):
        # p = Person()
        # self.add(p)
        # self.wait(2)
        # p.set_status("I")
        # self.wait(2)
        # p.set_status("R")
        C = SIRSimulation(n_citizen_per_city=50)
        self.add(C)
        def count():
            c = 0
            for p in C.people:
                if p.status == "I":
                    c += 1
            return (c == 0)
        self.wait_until(count)
        self.wait(5)
