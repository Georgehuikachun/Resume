const addBtn=document.querySelector("#addBtn")
const taskInput=document.querySelector("#taskInput")
const taskList=document.querySelector("#taskList")

addBtn.addEventListener("click", ()=>{
    const taskText= taskInput.value.trim();
    if (taskText==='') return;

    //Create <li>
    const li=document.createElement("li");
    li.innerHTML=`${taskText} <button class="delete-btn">Delete</button>`;

    //Delete btn fcn
    li.querySelector(".delete-btn").addEventListener("click", () =>{
        li.remove();
    })

    //add to list
    taskList.appendChild(li);

    //clear input
    taskInput.value="";
});

li.addEventListener("click", ()=>{
    li.classList.toggle("completed");
})