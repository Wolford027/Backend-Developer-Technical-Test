from sqlalchemy.orm import Session
import models, schemas

def get_notes(db: Session):
    return db.query(models.Note).order_by(models.Note.created_at.desc()).all()

def get_note(db: Session, note_id: int):
    return db.query(models.Note).filter(models.Note.id == note_id).first()

def create_note(db: Session, note: schemas.NoteCreate):
    db_note = models.Note(title=note.title, content=note.content)
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

def update_note(db: Session, note_id: int, note: schemas.NoteUpdate):
    db_note = get_note(db, note_id)
    if not db_note:
        return None
    for key, value in note.dict(exclude_unset=True).items():
        setattr(db_note, key, value)
    db.commit()
    db.refresh(db_note)
    return db_note

def delete_note(db: Session, note_id: int):
    db_note = get_note(db, note_id)
    if not db_note:
        return None
    db.delete(db_note)
    db.commit()
    return db_note