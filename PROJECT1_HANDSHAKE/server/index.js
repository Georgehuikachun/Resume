const express=require('express');
const cors=require('cors');
const app=express();

app.use(cors());

app.get('/api/hello',(req,res)=>{
    res.json({message:"Hello from Node.js!"});
}
);

const PORT=3001;
app.listen(PORT,()=> {
    console.log(`Server is running on http://localhost:${PORT}`);
});