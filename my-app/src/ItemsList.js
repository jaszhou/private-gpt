import React, { useEffect, useState } from 'react'; 

function ItemsList() {  
    const [items, setItems] = useState([]); 
 
    useEffect(() => { 
        fetch('http://localhost:5000/dev/db')
            .then(response => response.json())
            .then(data => setItems(data)); 
    }, []); 

    return (
        <ul>
            {items.map((item, index) => (    
                <li key={index}>{item}</li> 
            ))}
        </ul>
    );
}
export default ItemsList;