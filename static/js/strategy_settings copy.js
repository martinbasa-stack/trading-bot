
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

        //Trigger events 
        changeAssetManagerSymbols(generalTable)
        changeOnassetManagerTarget(generalTable)

        // Use hasOwnProperty to ensure you're only accessing own properties, not inherited ones        
        for (const key in StrategySettingsData[i]) { ////Go trough all keys in strategy
            
            if (StrategySettingsData[i].hasOwnProperty(key)) {
                if(key.includes("Dynamic")){ //// in dynamic buy sell indexes
                    for (let j = 0; j < StrategySettingsData[i][key].length; j++){    
                    if (StrategySettingsData[i][key][j]["Type"]){   //check if it is not an epty dictionary
                        let side ;
                        let tableId ;                  
                        if(key.includes("Buy")){ //create variables
                            side = "Buy";
                            tableId = `buyTable${StrategySettingsData[i]['id']}`;
                        } else {    
                            side = "Sell";
                            tableId = `sellTable${StrategySettingsData[i]['id']}`;
                        }                   
                        let addedRow = addRow(tableId,side); //Create a row
                        //Populate the row created
                        addedRow.querySelector('#Type').value = StrategySettingsData[i][key][j]["Type"]; //Get elemet imput 
                        addedRow.querySelector('#Comparator').value = StrategySettingsData[i][key][j]["Comparator"]; //Get elemet impu
                        addedRow.querySelector('#Value').value = StrategySettingsData[i][key][j]["Value"]; //Get elemet imput of value
                        addedRow.querySelector('#Value2').value = StrategySettingsData[i][key][j]["Value2"]; //Get elemet imput of value
                        addedRow.querySelector('#Weight').value = StrategySettingsData[i][key][j]["Weight"]; //Get elemet imput of value
                        addedRow.querySelector('#TradeOffset').value = StrategySettingsData[i][key][j]["BlockTradeOffset"]; //Get elemet imput of value 
                        addedRow.querySelector('#Trigger').value = StrategySettingsData[i][key][j]["Trigger"]; //Get elemet imput of trigger
                        addedRow.querySelector('#TriggerSelect').value = StrategySettingsData[i][key][j]["TriggerSelect"]; //Get elemet imput of trigger     
                        addedRow.querySelector('#OutputSelect').value = StrategySettingsData[i][key][j]["OutputSelect"]; //Get elemet imput of trigger                       
                        addedRow.querySelector('#Interval').value = StrategySettingsData[i][key][j]["Interval"];
                        if (StrategySettingsData[i][key][j]["Enable"]){
                        addedRow.querySelector('#Enable').value = 1; //
                        } else { 
                        addedRow.querySelector('#Enable').value = 0; //
                        }
                        addedRow.querySelector('#Factor').value = StrategySettingsData[i][key][j]["Factor"]; //Ge
                        addedRow.querySelector('#Max').value = StrategySettingsData[i][key][j]["Max"]; //Get e
                        //trigger events
                        changeOnTypechange(addedRow.querySelector('#Type'));
                        changeOnEnablechange(addedRow.querySelector('#Enable'));      
                    }}
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

