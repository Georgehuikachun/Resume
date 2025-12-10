import { useEffect, useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'

function App() {
  const [message,setMessage]=useState('calling backend')

  useEffect(()=>{
    fetch('http://localhost:3001/api/hello')
    .then(res=>res.json())
    .then(data=> setMessage(data.message))
    .catch(err=>setMessage('connection error, please check if backend is on'))
  },[])

  return (
    <div>
      <h1>Full stack handshake</h1>
      <h3>FrontEnd 5173 Ready!</h3>
      <h3>BackEnd 3001 Reply</h3>
      <h2>{message}</h2>
    </div>
  )
}

export default App
