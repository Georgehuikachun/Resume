const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose'); 
const app = express();

app.use(cors());
app.use(express.json());


const MONGO_URI = "mongodb+srv://georgehuikachun_db_user:EqeSuQ65nvKqWlqw@cluster0.dn8qzjw.mongodb.net/?appName=Cluster0";
// 1. connect to MONGODB
mongoose.connect(MONGO_URI)
    .then(() => console.log("Succeed to connect"))
    .catch(err => console.log("Failed to connect:"));

// 2.define schema
const NoteSchema = new mongoose.Schema({
    content: String
});
// 3.set model 
const Note = mongoose.model('Note', NoteSchema);

// 4. define Get all notes
app.get('/api/notes', async (req, res) => {
    const notes = await Note.find();
    res.json(notes);
});

// 5. define Post note
app.post('/api/notes', async (req, res) => {
    // new Note.save()
    const newNote = new Note({
        content: req.body.content
    });
    
    await newNote.save();
    
    res.json(newNote);
});

const PORT = 3001;
app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});