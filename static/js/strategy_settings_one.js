import { IndicatorRow } from "./moduls/IndicatorRow.js";

const StrategySettingsData = JSON.parse(
    document.getElementById("strategy").dataset.json
);

//Fill content on page load
 window.onload = function() {
    //Fill data to GeneralTable
    //const generalTable = document.querySelector(`#generalT_${StrategySettingsData['id']}`);  //Get table and fill the values  
    const generalTable = document.querySelector(`#div_${StrategySettingsData['id']}`);  //Get table and fill the values        
    generalTable.querySelector('#assetManagerTarget').value = StrategySettingsData['assetManagerTarget'];
    generalTable.querySelector('#assetManagerSymbol').value = StrategySettingsData['assetManagerSymbol'];
    generalTable.querySelector('#assetManageMaxSpendLimit').value = StrategySettingsData['assetManageMaxSpendLimit'];
    generalTable.querySelector('#assetManageMinSaveLimit').value = StrategySettingsData['assetManageMinSaveLimit'];
    generalTable.querySelector('#assetManagePercent').value = StrategySettingsData['assetManagePercent'];
    generalTable.querySelector('#BuyMin').value = StrategySettingsData['BuyMin'];
    generalTable.querySelector('#SellMin').value = StrategySettingsData['SellMin'];
    generalTable.querySelector('#type').value = StrategySettingsData['type'];

    //Trigger events 
    changeAssetManagerSymbols(generalTable)
    changeOnassetManagerTarget(generalTable)

    // Use hasOwnProperty to ensure you're only accessing own properties, not inherited ones        
    for (const key in StrategySettingsData) { ////Go trough all keys in strategy
        
        if (StrategySettingsData.hasOwnProperty(key)) {
            if(key.includes("Dynamic")){ //// in dynamic buy sell indexes
                let side ;
                let tableId ;
                let addButtonId;
                const idx = StrategySettingsData.id;  
                if(key.includes("Buy")){ //create variables
                    side = "Buy";
                    tableId = `buyTable${idx}`;
                    addButtonId = `#add_buy_${idx}`
                } else {    
                    side = "Sell";
                    tableId = `sellTable${idx}`;
                    addButtonId = `#add_sell_${idx}`
                }
                const addButton = this.document.getElementById(tableId).querySelector(addButtonId)         
                addButton.addEventListener('click', () => addRow(tableId, side)); 

                for (let j = 0; j < StrategySettingsData[key].length; j++){    
                if (StrategySettingsData[key][j]["Type"]){   //check if it is not an epty dictionary
                    const row = addRow(tableId, side);
                    row.load(StrategySettingsData[key][j]); // fill row with Flask data        
                }}
            }
        }
    }
 }
function addRow(tableId, side){    
    const tbody = document.getElementById(tableId).querySelector("tbody");
    const row = new IndicatorRow(tbody, side);
    return row
}
