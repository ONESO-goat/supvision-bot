import uuid


UUIDString = str 
def create_id()->UUIDString:
    return str(uuid.uuid4())