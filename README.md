# Mobile Systems for Time-relevant Modal shift

## Use, Contribute, and Extend!
We hope this repository inspires further developments in the field of Smart Mobility and Data Analysis for Intelligent Transportation.

Please acknowledge and cite this repository if you use the code. 

You are also most welcome to contribute to extend the code.


## How to Use
If you plan to test this whole repository for your project: 

1. Start by running 'run_update_from_new_legs.py':

Detects full door-to-door trips from the input trip-segments, and then computes alternative paths for those trips using different modes of transport (i.e. public transport, bike, and walk):

Use 'run_update_from_new_legs_parallel.py' instead, to considerably speedup the process when you have a large amount of data.


2. Run 'run_session_prepare_data.py':

Prepares session data suitable for analysis and visualization.


3. Use the session data as you wish. 

You can write your own visualization code and also use plotting functions already available in the 'tslib' package. 


## Code Guide
The 'tslib' package contains handy modules for analysis of trip-segments, advanced visualization, etc. These modules have been imported and used throughout the code.

The 'dal' package contains all the SQL code and database interface.

The 'commonlayer' package contains HTTP REST API code.

The important 'pyfiles.common.otp_trip_planner' module uses OpenTripPlanner (OTP) to compute detailed origin-destination trip paths according to the desired mode of transportation.
OTP is a powerful tool but can be tricky to use. See how it is used in this repository for tips and tricks and to get ideas. The code is faily documented.




