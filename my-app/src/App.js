import logo from './logo.svg';
import './App.css';
import React from "react";
import ItemsList from './ItemsList';

function App_DB() { 
  return ( 
    <div className="App">  
      <h1>Items</h1>  
      <ItemsList /> 
    </div>
  );
}
function Example() {
  return <button className="btn btn-primary">Click me</button>;
}


function App() {
  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p>
          Edit <code>src/App.js</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React
        </a>
      </header>
    </div>
  );
}

export default App_DB;

// export default Example;