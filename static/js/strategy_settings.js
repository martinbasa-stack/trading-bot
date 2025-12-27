import { IndicatorRow } from "./moduls/IndicatorRow.js";

const StrategySettingsData = JSON.parse(
    document.getElementById("StrategySettingsData").dataset.json
);

const scrolIndex = JSON.parse(
    document.getElementById("scrollId").dataset.json
);

//Fill content on page load
 window.onload = function() {
    for (let i = 0; i < StrategySettingsData.length; i++) { // In strategy
        //Fill data to GeneralTable
        //console.log(`#div_${StrategySettingsData[i]['id']}`);
        if (StrategySettingsData[i]['id'] === 'backtester') {
            continue; // Skips the rest of the loop body for this iteration
        }
        //const generalTable = document.querySelector(`#generalT_${StrategySettingsData[i]['id']}`);  //Get table and fill the values  
        const generalTable = document.querySelector(`#div_${StrategySettingsData[i]['id']}`);  //Get table and fill the values        
        generalTable.querySelector('#assetManagerTarget').value = StrategySettingsData[i]['assetManagerTarget'];
        generalTable.querySelector('#assetManagerSymbol').value = StrategySettingsData[i]['assetManagerSymbol'];
        generalTable.querySelector('#assetManageMaxSpendLimit').value = StrategySettingsData[i]['assetManageMaxSpendLimit'];
        generalTable.querySelector('#assetManageMinSaveLimit').value = StrategySettingsData[i]['assetManageMinSaveLimit'];
        generalTable.querySelector('#assetManagePercent').value = StrategySettingsData[i]['assetManagePercent'];
        generalTable.querySelector('#BuyMin').value = StrategySettingsData[i]['BuyMin'];
        generalTable.querySelector('#SellMin').value = StrategySettingsData[i]['SellMin'];
        generalTable.querySelector('#type').value = StrategySettingsData[i]['type'];

        //Trigger events 
        changeAssetManagerSymbols(generalTable)
        changeOnassetManagerTarget(generalTable)

        // Use hasOwnProperty to ensure you're only accessing own properties, not inherited ones        
        for (const key in StrategySettingsData[i]) { ////Go trough all keys in strategy
            
            if (StrategySettingsData[i].hasOwnProperty(key)) {
                if(key.includes("Dynamic")){ //// in dynamic buy sell indexes
                    let side ;
                    let tableId ;
                    let addButtonId;
                    const idx = StrategySettingsData[i].id;  
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

                    for (let j = 0; j < StrategySettingsData[i][key].length; j++){ //Run trough list of indicators
                        if (StrategySettingsData[i][key][j]["Type"]){   //check if it is not an epty dictionary      
                            const row = addRow(tableId, side);
                            row.load(StrategySettingsData[i][key][j]); // fill row with Flask data                            
                        }
                    }
                }
            }
        }

    }
    const aboutSection = this.document.getElementById(scrolIndex);
    aboutSection.scrollIntoView({      
        block: 'start',
        behavior: 'instant'
    });
 }


function addRow(tableId, side){    
    const tbody = document.getElementById(tableId).querySelector("tbody");
    const row = new IndicatorRow(tbody, side);
    return row;
}   