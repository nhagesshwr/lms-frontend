import sys
import os
import traceback

# Add parent directory to path to find app module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from app.database import SessionLocal
    from app.models import Employee, Enrollment, Course
    from app.routes.activity import get_recent_activity
except Exception as e:
    print(f"Error importing modules: {e}")
    traceback.print_exc()
    sys.exit(1)

db = SessionLocal()
try:
    # Use any employee or super admin to test
    emp = db.query(Employee).first()
    if not emp:
        print("No employees found in database.")
    else:
        print(f"Testing with user: {emp.name} (ID: {emp.id})")
        # Manually call the backend function
        import types
        from fastapi import Query
        
        # Call the backend function
        acts = get_recent_activity(limit=100, type_filter=None, db=db, current_user=emp)
        print(f"Total events found: {len(acts)}")
        if len(acts) > 0:
            for act in acts[:5]:
                print(f"- {act['time']} : {act['user']} {act['action']} ({act['detail']})")
        else:
            print("No events returned (empty list).")
except Exception as e:
    print(f"ERROR RUNNING ACTIVITY LOGIC: {e}")
    traceback.print_exc()
finally:
    db.close()
