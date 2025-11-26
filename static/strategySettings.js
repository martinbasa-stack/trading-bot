 //Event listner for all changes made on page filter out in function
const StrategySettingsData = JSON.parse(
    document.getElementById("StrategySettingsData").dataset.json
);

const scrolIndex = JSON.parse(
    document.getElementById("scrollId").dataset.json
);
//Scroling down
document.body.addEventListener('click', function(event) {
    const selectedElement = event.target; //Get actual element
    if(selectedElement.id.includes('nav_') ){
    const aboutSection = document.getElementById(selectedElement.value);
    aboutSection.scrollIntoView({    
        block: 'start',
        behavior: 'smooth'
    });
    }
});
//Fill content on page load
 window.onload = function() {
    for (let i = 0; i < StrategySettingsData.length; i++) { // In strategy
        //Fill data to GeneralTable
        //console.log(StrategySettingsData[i]);
        const generalTable = document.querySelector(`#generalT_${StrategySettingsData[i]['id']}`);  //Get table and fill the values        
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
//on change selection boxes
document.body.addEventListener('change', function(event) {
    const selectedElement = event.target; //Get actual element
    // Check if the event target is a <select> element
    if (selectedElement.tagName === 'SELECT') {
        const selectedValue = selectedElement.value;
        const selectedRow = selectedElement.parentElement.parentElement;
        //hide inputs not relevante to indicator
        if (selectedElement.id === 'Type'){
            changeOnTypechange(selectedElement);
        }
        if (selectedElement.id === 'TriggerSelect'){
            changeTriggerSelect(selectedElement);
        }
        //Dim factor if not enabled
        if (selectedElement.id === 'Enable'){
            changeOnEnablechange(selectedElement);
        }
        //Hide for asset manager depending on target
        if (selectedElement.id === 'assetManagerTarget'){
            const selectedTable = selectedElement.parentElement.parentElement.parentElement;
            changeOnassetManagerTarget(selectedTable);
        }
        //Change for asset manager depending on Symbol
        if (selectedElement.id === 'assetManagerSymbol'){
            const selectedTable = selectedElement.parentElement.parentElement.parentElement;
            changeAssetManagerSymbols(selectedTable);
        }
    }   
        //Change BuyMinValue depending on base value
    if (selectedElement.id === 'BuyBase'){
        changeBaseEvent('#BuyMin', selectedElement);        
    }
       //Change SellMinValue depending on base value
    if (selectedElement.id === 'SellBase'){
        changeBaseEvent('#SellMin', selectedElement);        
    }
});



//Catch imput from ALL
//const myInputSymbol1 = document.getElementById('Symbol1');
document.body.addEventListener('input', (event) => {
    const inputElement = event.target;
    //Check if imput is Symbol1
    if (inputElement.id ==="Symbol1"){
        // Access the current element of the input field
        const selectedTable = inputElement.parentElement.parentElement.parentElement;
        const assetManagerSymbol1 = selectedTable.querySelector('#assetManagerSymbol1'); //Get elemet 
        //Edit values wher Symbol used            
        assetManagerSymbol1.innerText = inputElement.value; 
        changeAssetManagerSymbols(selectedTable)
    } 
    //Check if imput is Symbol2
    if (inputElement.id ==="Symbol2"){
        // Access the current element of the input field
        const selectedTable = inputElement.parentElement.parentElement.parentElement;
        const tagBuyBase = selectedTable.querySelector('#BuyBaseUnit'); //Get elemet 
        const tagSellBase = selectedTable.querySelector('#SellBaseUnit'); //Get elemet 
        const assetManagerSymbol2 = selectedTable.querySelector('#assetManagerSymbol2'); //Get elemet         
        const BuyMinUnit = selectedTable.querySelector('#BuyMinUnit');
        const SellMinUnit = selectedTable.querySelector('#SellMinUnit');
        //Edit values wher Symbol used            
        tagBuyBase.innerText = " " + inputElement.value;
        tagSellBase.innerText = " " + inputElement.value;   
        BuyMinUnit.innerText = " " + inputElement.value;   
        SellMinUnit.innerText = " " + inputElement.value;     
        assetManagerSymbol2.innerText = inputElement.value;     
        changeAssetManagerSymbols(selectedTable)
    }     
});
/////////////////////////////////////////////////////////////Functions

function changeBaseEvent(textMin, selectedElement){
    const selectedValue = selectedElement.value;
    const selectedTable = selectedElement.parentElement.parentElement.parentElement;
    const sideMin = selectedTable.querySelector(textMin);
    if (sideMin.value < selectedValue*0.1){
        sideMin.value = selectedValue*0.1;
    }
    if (sideMin.value > selectedValue){
        sideMin.value = selectedValue;
    }
}
function changeAssetManagerSymbols(selectedTable){    
    const symbol1 = selectedTable.querySelector("#Symbol1");
    const symbol2 = selectedTable.querySelector("#Symbol2");
    const TAGassetManageMaxSpendLimitText = selectedTable.querySelector('#assetManageMaxSpendLimitText');
    const TAGassetManageMinSaveLimitText = selectedTable.querySelector('#assetManageMinSaveLimitText');
    const TAGassetManagerSymbol = selectedTable.querySelector('#assetManagerSymbol');
    if (TAGassetManagerSymbol.value == 1){ //Selected symbol is 1
        //Edit values             
        TAGassetManageMaxSpendLimitText.innerText =  symbol2.value;
        TAGassetManageMinSaveLimitText.innerText =  symbol1.value;  
    }else{ //Selected symbol is 2
        //Edit values             
        TAGassetManageMaxSpendLimitText.innerText =  symbol1.value;
        TAGassetManageMinSaveLimitText.innerText =  symbol2.value;  

    }
    
}
//Function when assetManagerTarget state is changed
function changeOnassetManagerTarget(selectedTable){        
    const selectedValue = selectedTable.querySelector('#assetManagerTarget').value;
    const TAGassetManagerSymbol = selectedTable.querySelector('#assetManagerSymbol');
    const TAGassetManageMaxSpendLimit = selectedTable.querySelector('#assetManageMaxSpendLimit');
    const TAGassetManageMinSaveLimit = selectedTable.querySelector('#assetManageMinSaveLimit');
    const TAGassetManagePercent = selectedTable.querySelector('#assetManagePercent');
    const TAGassetManagerSymbolText = selectedTable.querySelector('#assetManagerSymbolText');
    

    switch (selectedValue) {
        case 'None':
            TAGassetManagerSymbolText.innerText = "";
            TAGassetManagerSymbol.hidden = true;
            TAGassetManageMaxSpendLimit.className = "disabledLook"
            TAGassetManageMinSaveLimit.className = "disabledLook"
            TAGassetManagePercent.hidden = true;
            break; 
        case 'Account':
            TAGassetManagerSymbolText.innerText = "Save ";
            TAGassetManagerSymbol.hidden = false;
            TAGassetManageMaxSpendLimit.className = ""
            TAGassetManageMinSaveLimit.className = ""
            TAGassetManagePercent.hidden = false;
            break; 
        case 'Trades': 
            TAGassetManagerSymbolText.innerText = "Save ";
            TAGassetManagerSymbol.hidden = false;
            TAGassetManageMaxSpendLimit.className = ""
            TAGassetManageMinSaveLimit.className = ""
            TAGassetManagePercent.hidden = false;
            break; 
    }
}

//Function when type is changed
function changeOnTypechange(selectedElement){        
    const selectedValue = selectedElement.value;
    const selectedRow = selectedElement.parentElement.parentElement;
    const tagInRowTrigger = selectedRow.querySelector('#Trigger'); //Get elemet imput of trigger
    const tagInRowTriggerTextRight = selectedRow.querySelector('#pRTrigger'); //Get elemet imput of trigger
    const tagInRowTriggerTextLeft = selectedRow.querySelector('#pLTrigger'); //Get elemet imput of value 
    const tagInRowTriggerSelect = selectedRow.querySelector('#TriggerSelect'); //Get elemet imput of trigger
    const tagInRowOutputSelect = selectedRow.querySelector('#OutputSelect'); //Get elemet imput of trigger
    const tagInRowValue = selectedRow.querySelector('#Value'); //Get elemet imput of value
    const tagInRowTriggerOffset = selectedRow.querySelector('#TradeOffset'); //Get elemet imput of value 
    const tagInRowTradeOffsetText = selectedRow.querySelector('#pTradeOffset'); //Get elemet imput of value 
    const TAGInterval = selectedRow.querySelector('#Interval');
    //console.log(tagInRowTriggerSelect); 
    tagInRowTriggerSelect.hidden = true;
    tagInRowOutputSelect.hidden = true;
    tagInRowValue.type = "number";   
    tagInRowTrigger.type = "number";       
    tagInRowTriggerOffset.type = "number";
    TAGInterval.hidden = false;
    
    tagInRowTradeOffsetText.innerText = "";
    tagInRowTriggerTextRight.innerText = "";
    tagInRowTriggerTextLeft.innerText = selectedElement.value;
    switch (selectedValue) {
        case 'AvrageCost':
        case 'AvrageEntry':
        case 'AvrageExit':  
            tagInRowValue.type = "hidden";
            tagInRowTrigger.type = "hidden"; 
            TAGInterval.hidden = true;
            tagInRowTriggerTextRight.innerText = "PRICE";
            tagInRowTradeOffsetText.innerText = "%";
            break;
        case 'SMA':
        case 'EMA':
            //tagInRowTriggerTextRight.innerText = "PRICE";
            tagInRowTradeOffsetText.innerText = "%";
            tagInRowTriggerSelect.hidden = false;
            changeTriggerSelect(tagInRowTriggerSelect)
            break;
        case 'BB':
            tagInRowOutputSelect.hidden = false;           
            tagInRowTrigger.type = "hidden";
            tagInRowTradeOffsetText.innerText = "%";
            tagInRowTriggerTextLeft.innerText = "";
            tagInRowTriggerTextRight.innerText = "PRICE";
            break;            
        case 'Price':  ///After here no trigger offset needed 
        case 'F&G':
            tagInRowValue.type = "hidden";   
            TAGInterval.hidden = true;
        default: 
            tagInRowTriggerOffset.type = "hidden";
            tagInRowTriggerOffset.value = 0.0
    }
}
//Function when enable state is changed
function changeOnEnablechange(selectedElement){        
    const selectedValue = selectedElement.value;
    const selectedRow = selectedElement.parentElement.parentElement;
    let tagInRowFactor = selectedRow.querySelector('#Factor');
    let tagInRowMax = selectedRow.querySelector('#Max');       
    tagInRowFactor.className = "";   
    tagInRowMax.className = "";       
    
    if (selectedValue == 0) {
        tagInRowFactor.className = "disabledLook";   
        tagInRowMax.className = "disabledLook";                  
    }
}

//Function when enable state is changed
function changeTriggerSelect(selectedElement){        
    const selectedValue = selectedElement.value;
    const selectedRow = selectedElement.parentElement.parentElement;
    const tagInRowTrigger = selectedRow.querySelector('#Trigger'); //Get elemet imput of trigger  
 
     switch (selectedValue) {
        case 'Price':
            tagInRowTrigger.type = "hidden"; 
                break;
        default: 
            tagInRowTrigger.type = "number";
     }
}

function addRow(tableName, side, data) {
    var table = document.getElementById(tableName).getElementsByTagName('tbody')[0];
    var newRow = table.insertRow(); // Insert a new row at the end of the tbody

    // Create cells for the new row
    var cell1 = newRow.insertCell(0);
    var cell2 = newRow.insertCell(1);
    var cell3 = newRow.insertCell(2);
    var cell4 = newRow.insertCell(3);
    var cell5 = newRow.insertCell(4);
    var cell6 = newRow.insertCell(5);
    var cell7 = newRow.insertCell(6);
    var cell8 = newRow.insertCell(7);

    // Populate the cells with content (e.g., input fields or default text)
    cell1.innerHTML = `<select id="Type" name="Dynamic${side}Type">
                            <option value="SMA" >SMA</option>
                            <option value="EMA" >EMA</option>
                            <option value="BB" >Bol. Band</option>
                            <option value="RSI" >RSI</option>
                            <option value="ROC" >ROC</option>
                            <option value="ADX" >ADX</option>
                            <option value="F&G" >Fear & Gread</option>
                            <option value="AvrageCost">Average Cost</option>
                            <option value="AvrageEntry">Average Entry</option>
                            <option value="AvrageExit">Average Exit</option>
                            <option value="Price">Price</option>
                        </select>`;
    cell2.innerHTML = `<input type="number" min="0" step="1"  id="Value" name="Dynamic${side}Value" value = 20> 
                        <input type="hidden"  min="0" step="1" id="Value2" name="Dynamic${side}Value2" value = 0>
                        <input type="hidden"  min="0" step="1" id="Value3" name="Dynamic${side}Value3" value = 0>
                        <input type="hidden"  min="0" step="1" id="Value4" name="Dynamic${side}Value4" value = 0>
                        <select id="Interval" name="Dynamic${side}Interval">
                            <option value="30m" >30m</option>
                            <option value="1h" >1h</option>
                            <option value="2h" >2h</option>
                            <option value="4h" >4h</option>
                            <option value="6h" >6h</option>
                            <option value="8h" >8h</option>
                            <option value="12h" >12h</option>
                            <option selected value="1d">1d</option>
                            <option value="3d">3d</option>
                            <option value="1w">1w</option>
                            <option value="1M">1M</option>
                        </select>`;
    cell3.innerHTML = `<input type="number" min="0" step="1" id="Weight" name="Dynamic${side}Weight" value = 0 >`;
    cell4.innerHTML = `<input type="number" min="-90" max="90" step="0.01"  id="TradeOffset" name="Dynamic${side}BlockTradeOffset" value = 0>
                        <span  id="pTradeOffset" >%</span>`;
    cell5.innerHTML = `<select hidden name="Dynamic${side}OutputSelect" id="OutputSelect">
                            <option id="OutputSelect_0" value="Upper">Upper</option>
                            <option id="OutputSelect_1" value="Middle">Middle</option>
                            <option id="OutputSelect_2" value="Lower">Lower</option>
                        </select>    
                        <span id="pLTrigger">SMA</span>
                        <select id="Comparator" name="Dynamic${side}Comparator">
                            <option value="Above"> > </option>
                            <option value="Below"> < </option>
                        </select> 
                        <select hidden name="Dynamic${side}TriggerSelect" id="TriggerSelect">
                            <option value="Price">Price</option>
                            <option value="SMA">SMA</option>
                            <option value="EMA">EMA</option>
                        </select>    
                        <input type="hidden" id="Trigger" name="Dynamic${side}Trigger" value = 0 > 
                        <span id="pRTrigger">PRICE</span>`;
    cell6.innerHTML = `<select name="Dynamic${side}Enable" id="Enable">
                            <option value="1">ON</option>
                            <option value="0" selected>OFF</option>
                        </select>
                        <input class="disabledLook" type="number" min="0" step="0.1"  id="Factor" name="Dynamic${side}Factor" value = 0 > %`;
    cell7.innerHTML = `<input class="disabledLook" type="number" min="0" step="0.1"  id="Max" name="Dynamic${side}Max" value = 100.0 > %`;
    cell8.innerHTML = `<button onclick="removeRow(this)" type="button"  value="removeIndex" >REMOVE</button>`;

    return newRow;
    // Or with default text:
}
function removeRow(buttonElement) {
    // Get the parent <td> of the button
    const td = buttonElement.parentElement;
    // Get the parent <tr> of the <td>
    const tr = td.parentElement;
    // Remove the <tr> from its parent (the <tbody>)
    tr.remove();
}
