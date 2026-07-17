from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models, schemas, crud
from database import SessionLocal, engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Notes API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/notes", response_model=list[schemas.NoteOut])
def read_notes(db: Session = Depends(get_db)):
    return crud.get_notes(db)

@app.get("/notes/{note_id}", response_model=schemas.NoteOut)
def read_note(note_id: int, db: Session = Depends(get_db)):
    db_note = crud.get_note(db, note_id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    return db_note

@app.post("/notes", response_model=schemas.NoteOut, status_code=201)
def create_note(note: schemas.NoteCreate, db: Session = Depends(get_db)):
    return crud.create_note(db, note)

@app.put("/notes/{note_id}", response_model=schemas.NoteOut)
def update_note(note_id: int, note: schemas.NoteUpdate, db: Session = Depends(get_db)):
    db_note = crud.update_note(db, note_id, note)
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    return db_note

@app.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int, db: Session = Depends(get_db)):
    if not crud.delete_note(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}


@app.get("/api/health")
def health():
    return {"status": "ok"}
