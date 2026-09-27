#!/usr/bin/env python3
import math

class SwarmPlanner:
    def __init__(self, arena_x_start=75.0, arena_width=1000.0, arena_height=1000.0):
        self.x_start = arena_x_start
        self.x_end = arena_x_start + arena_width
        self.y_min = 50.0
        self.y_max = arena_height - 50.0

    def generate_survey_corridors(self, sector_id, total_sectors=2):
        corridor_height = (self.y_max - self.y_min) / total_sectors
        y_bottom = self.y_min + (sector_id * corridor_height)
        y_top = y_bottom + corridor_height
        
        waypoints = []
        x_steps = [self.x_start + 100.0, self.x_start + 350.0, self.x_start + 650.0, self.x_start + 900.0]
        
        up = True
        for x in x_steps:
            if up:
                waypoints.append([x, y_bottom + 30.0, 40.0])
                waypoints.append([x, y_top - 30.0, 40.0])
            else:
                waypoints.append([x, y_top - 30.0, 40.0])
                waypoints.append([x, y_bottom + 30.0, 40.0])
            up = not up
            
        return waypoints

    def get_relay_stations(self, num_relays=2):
        stations = []
        for i in range(1, num_relays + 1):
            stations.append([i * 85.0, 500.0, 30.0 + (i * 5.0)])
        return stations
