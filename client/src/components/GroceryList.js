import React, { useState, useEffect } from "react";
import axios from "axios";
import "./GroceryList.css";

axios.defaults.withCredentials = true;

const GroceryList = () => {
  const [items, setItems] = useState([]);
  const [newItem, setNewItem] = useState("");
  const [simulatedDate, setSimulatedDate] = useState("");
  const [generatedList, setGeneratedList] = useState([]);
  const [tempItems, setTempItems] = useState([]);
  const [deletedItems, setDeletedItems] = useState([]);
  const [confirmedItems, setConfirmedItems] = useState([]);
  const [showGroceryList, setShowGroceryList] = useState(false);

  useEffect(() => {
    fetchItems();
  }, []);

  const fetchItems = async () => {
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/items`
      );
      console.log("Fetched items:", response.data);
      setItems(response.data);
      setTempItems([]);
      setConfirmedItems([]);
    } catch (error) {
      console.error("Error fetching items:", error);
      alert("Failed to fetch items");
    }
  };

  const addItem = () => {
    if (!newItem.trim()) {
      alert("Item name cannot be empty");
      return;
    }

    const existingItemNamesForDate = items
      .filter(
        (item) =>
          item.date ===
          (simulatedDate || new Date().toISOString().split("T")[0])
      )
      .map((item) => item.name);
    const tempItemNames = tempItems.map((item) => item.name);

    if (
      !existingItemNamesForDate.includes(newItem) &&
      !tempItemNames.includes(newItem)
    ) {
      const newItemObject = { _id: Date.now().toString(), name: newItem };
      console.log("Adding new item to tempItems:", newItemObject);
      setTempItems([...tempItems, newItemObject]);
    } else {
      alert("Item already exists for the selected date");
    }
    setNewItem("");
    setShowGroceryList(true);
  };

  const deleteItem = (id) => {
    if (!id) {
      alert("Item ID is undefined");
      return;
    }
    console.log("Deleting item with ID:", id);
    setTempItems(tempItems.filter((item) => item._id !== id));
    setDeletedItems([...deletedItems, id]);
  };

  const submitWeeklyList = async () => {
    try {
      const itemNames = tempItems.map((item) => ({ name: item.name }));
      const date = simulatedDate || new Date().toISOString().split("T")[0];

      console.log(
        "Submitting weekly list with items:",
        itemNames,
        "and date:",
        date
      );

      await axios.post(`${process.env.REACT_APP_API_URL}/items/weekly`, {
        items: itemNames,
        date: date,
      });

      for (const itemId of deletedItems) {
        if (itemId.length === 24) {
          console.log("Deleting item from database with ID:", itemId);
          await axios.delete(
            `${process.env.REACT_APP_API_URL}/items/${itemId}`
          );
        }
      }

      fetchItems();
      setDeletedItems([]);
    } catch (error) {
      console.error("Error submitting weekly list:", error);
      alert("Failed to submit weekly list");
    }
  };

  const generateList = async () => {
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/autogenerate`,
        {
          params: { date: simulatedDate },
        }
      );
      console.log("Generated list:", response.data.generated_list);
      setGeneratedList(response.data.generated_list);
    } catch (error) {
      console.error("Error generating list:", error);
      alert("Failed to generate list");
    }
  };

  const confirmPurchase = (item) => {
    console.log("Confirming purchase for item:", item);
    setConfirmedItems([...confirmedItems, item]);
  };

  const submitAutoGeneratedList = async () => {
    try {
      console.log(
        "Submitting auto-generated list with confirmed items:",
        confirmedItems
      );
      await axios.post(`${process.env.REACT_APP_API_URL}/items/confirm`, {
        items: confirmedItems,
        date: simulatedDate || new Date().toISOString().split("T")[0],
      });
      fetchItems();
      setConfirmedItems([]);
      setGeneratedList([]);
    } catch (error) {
      console.error("Error submitting auto-generated list:", error);
      alert("Failed to submit auto-generated list");
    }
  };

  return (
    <div class = "groceryList" >
      <h1>Grocery List</h1>
      <div>
        <input
          type="text"
          placeholder="Add new item"
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
        />
        <button onClick={addItem}>Add Item</button>
      </div>
      {showGroceryList && (
        <ul>
          {tempItems.map((item) => (
            <li key={item._id}>
              {item.name}
              <button onClick={() => deleteItem(item._id)}>Delete</button>
            </li>
          ))}
        </ul>
      )}
      <button onClick={submitWeeklyList}>Update List</button>
      <div>
        <input
          type="date"
          value={simulatedDate}
          onChange={(e) => setSimulatedDate(e.target.value)}
        />
      </div>
      <button onClick={generateList}>Generate List</button>
      <h2>Generated List</h2>
      <ul>
        {generatedList.map((item) => (
          <li key={item}>
            {item}
            <button onClick={() => confirmPurchase(item)}>
              Confirm Purchase
            </button>
          </li>
        ))}
      </ul>
      {generatedList.length > 0 && (
        <button onClick={submitAutoGeneratedList}>
          Update Auto-Generated List
        </button>
      )}
    </div>
  );
};

export default GroceryList;