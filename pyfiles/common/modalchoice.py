from enum import Enum

class CarNonCarEnum(Enum): 
    CAR = 'CAR'
    NONCAR = 'NONCAR'

PublicTransportModesTemplate = {'BUS', 'TRAM', 'RAIL', 'SUBWAY', 'FERRY'}

class ModalChoice:

    def __init__(self):
        pass
    
    @classmethod
    def get_car_noncar_mode(cls, mode):
        if mode in {'CAR'}:
            return CarNonCarEnum.CAR
        else:
            return CarNonCarEnum.NONCAR
    
    @classmethod
    def get_leg_activity_name(self, leg):
        if leg['line_source'] is not None and leg['line_source'] == 'USER':            
            if leg['line_type'] in {'FERRY', 'SUBWAY', 'TRAIN', 'TRAM', 'BUS'}:
                #print("changed to IN_VEHICLE by USER")
                return 'IN_VEHICLE'
            else:
                #print("changed to",leg['line_type'],"by USER")
                return leg['line_type']
        else:
            return leg['activity']

    @classmethod
    def get_leg_line_type(self, leg):
        if leg['line_source'] is not None and leg['line_source'] == 'USER':                    
            if leg['line_type'] in {'FERRY', 'SUBWAY', 'TRAIN', 'TRAM', 'BUS'}:
                #print("changed to",leg['line_type'],"by USER")
                return leg['line_type']
            else:
                #print("changed to None by USER")
                return None
        else:
            return leg['line_type']

    @classmethod
    def is_car_leg(self, leg):
        if leg['activity'] == 'IN_VEHICLE' and leg['line_type'] is None:
            return True
        return False
