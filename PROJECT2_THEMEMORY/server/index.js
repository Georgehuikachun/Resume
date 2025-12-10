const express=require('express');
const cors=require('cors');
const { log } = require('console');
const app=express();

app.use(cors());

app.use(express.json());
let notes=[{id:1, content: "Item 1"},
            {id:2, content: "Item 2"}
];

app.get('/api/notes',(req,res)=>{
    res.json(notes);
}
);

app.post('/api/notes',(req,res)=>{
    const newNote=req.body;
    newNote.id=notes.length +1;
    notes.push(newNote);
    console.log("New note received:",newNote);
    res.json(newNote);
});

const PORT=3001;
app.listen(PORT,()=> {
    console.log(`Server is running on http://localhost:${PORT}`);
});