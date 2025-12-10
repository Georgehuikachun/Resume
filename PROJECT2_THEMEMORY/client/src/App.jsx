import { useEffect, useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'

function App() {
  // Define changing states
  const [notes,setNotes]=useState([])
  const [input,setInput]=useState('')
  // initialise page
  useEffect(()=>{
    fetchNotes();
  },[])
  // define get action
  const fetchNotes =async()=>{
    const res=await fetch('http://localhost:3001/api/notes');
    const data=await res.json();
    setNotes(data);
  }
  // define the post, refresh page, and clear input box
  const handleAddNote =async()=>{
    if (!input) return;

    await fetch('http://localhost:3001/api/notes',{
      method: 'POST',
      headers:{
        'Content-Type':'application/json'
      },
      body: JSON.stringify({content:input})
    })
    // ask with get method to get the lastest and update current page
    fetchNotes();
    setInput('');
  }

  return (
    <div style={{padding:'50px'}}>
      <h1>The Memory</h1>
      <div style={{marginBottom:'20px'}}>
        <input 
          type="text"
          value={input}
          onChange={(e)=> setInput(e.target.value)}
          placeholder='ADD SOME TEXT'
          style={{padding:'10px', width:'200px'}}>
        </input>
        <button 
          onClick={handleAddNote}
          style={{padding:'10px',marginLeft:'10px'}}>ADD NOTE</button>
      </div>
      <ul>
        {notes.map(note=>(
          <li key={note.id} style={{marginBottom:'10px'}}>
            {note.id}. {note.content}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default App
