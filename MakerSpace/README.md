##MAKERSPACE PROGRAM
It is a program that is going to record all the members taking equipments from MakerSpace store and also update upon the return of the loan.
The program is made of four modules that all work interdependently to one another. The modules are;
-Services.py
-models.py
-database.py
-main.py
Each model save an important role in making features in the program work as planned.
1. Services.py
This module is responsible for all the logics in the program through the services such as members service, equipment service, Loan service and report service.Also service.py is responsible for validation of input, whenever the user input the invalid input it flags out without crashing the entire system.
2. Models.py
This module is responsible for giving typed  object to the program instead of of raw sqlite3. It touches the concept of object oriented programming (OOP)
It is not responsible for logics. In this module I created three classes that are for members, equipment and loan and per each class I defined the methods andproperties that they have.
3. Database.py
This module is the one that owns single SQLITE and schema. It is the center for the connection with the rest of the modules through database instances 
4. Main.py
This is the executable file in the program. It is responsible for displaying all the menus, it only takes user input and print to allow the user to interact with the program. It delegates logics to the services.py
## The following are the features that the program will be having:
-Register members
-Update members
-List members
-Delete members
-Register available equipments
-Update equipments
-List equipments
-Delete equipments
-Loan checkin
-Loan checkout
-Reports

In addition, On the part of delete feature the program can only delete the member or the tool if no loan is associated but if it happen that the member has a loan it can not allow the name to be deleted.
