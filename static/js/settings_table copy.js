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
            const selectedDiv = selectedElement.closest("div")
            console.log(selectedDiv)
            changeOnassetManagerTarget(selectedElement);
        }
        //Change for asset manager depending on Symbol
        if (selectedElement.id === 'assetManagerSymbol'){
            changeAssetManagerSymbols(selectedElement);
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
        // Access the current element of the input fiel
        const selectedDiv = inputElement.closest("div"); 
        const assetManagerSymbol1 = selectedDiv.querySelector('#assetManagerSymbol1'); //Get elemet 
        //Edit values wher Symbol used            
        assetManagerSymbol1.innerText = inputElement.value; 
        changeAssetManagerSymbols(selectedDiv)
    } 
    //Check if imput is Symbol2
    if (inputElement.id ==="Symbol2"){
        // Access the current element of the input field
        const selectedDiv = inputElement.closest("div"); 
        const tagBuyBase = selectedDiv.querySelector('#BuyBaseUnit'); //Get elemet 
        const tagSellBase = selectedDiv.querySelector('#SellBaseUnit'); //Get elemet 
        const assetManagerSymbol2 = selectedDiv.querySelector('#assetManagerSymbol2'); //Get elemet         
        const BuyMinUnit = selectedDiv.querySelector('#BuyMinUnit');
        const SellMinUnit = selectedDiv.querySelector('#SellMinUnit');
        //Edit values wher Symbol used            
        tagBuyBase.innerText = " " + inputElement.value;
        tagSellBase.innerText = " " + inputElement.value;   
        BuyMinUnit.innerText = " " + inputElement.value;   
        SellMinUnit.innerText = " " + inputElement.value;     
        assetManagerSymbol2.innerText = inputElement.value;     
        changeAssetManagerSymbols(inputElement)
    }     
});

/////////////////////////////////////////////////////////////Functions
//Asset events
function changeBaseEvent(textMin, selectedElement){
    const selectedValue = selectedElement.value;
    const selectedDiv = selectedElement.closest("div"); 
    const sideMin = selectedDiv.querySelector(textMin);
    if (sideMin.value < selectedValue*0.1){
        sideMin.value = selectedValue*0.1;
    }
    if (sideMin.value > selectedValue){
        sideMin.value = selectedValue;
    }
}

function changeAssetManagerSymbols(selectedElement){ 
    const selectedDiv = selectedElement.closest("div");  
    const symbol1 = selectedDiv.querySelector("#Symbol1");
    const symbol2 = selectedDiv.querySelector("#Symbol2");
    const TAGassetManageMaxSpendLimitText = selectedDiv.querySelector('#assetManageMaxSpendLimitText');
    const TAGassetManageMinSaveLimitText = selectedDiv.querySelector('#assetManageMinSaveLimitText');
    const TAGassetManagerSymbol = selectedDiv.querySelector('#assetManagerSymbol');
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
function changeOnassetManagerTarget(selectedElement){        
    const selectedDiv = selectedElement.closest("div");
    const selectedValue = selectedDiv.querySelector('#assetManagerTarget').value;
    const TAGassetManagerSymbol = selectedDiv.querySelector('#assetManagerSymbol');
    const TAGassetManageMaxSpendLimit = selectedDiv.querySelector('#assetManageMaxSpendLimit');
    const TAGassetManageMinSaveLimit = selectedDiv.querySelector('#assetManageMinSaveLimit');
    const TAGassetManagePercent = selectedDiv.querySelector('#assetManagePercent');
    const TAGassetManagerSymbolText = selectedDiv.querySelector('#assetManagerSymbolText');
    

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

//Indicator events
//Function when type is changed
function changeOnTypechange(selectedElement){        
    const selectedValue = selectedElement.value;
    const selectedRow = selectedElement.closest("tr"); 
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
    tagInRowTrigger.min = "0"; 
    tagInRowTrigger.step = "0.01";    
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
            tagInRowValue.value = 0;
            tagInRowTrigger.type = "hidden"; 
            TAGInterval.hidden = true;
            tagInRowTriggerTextRight.innerText = "PRICE";
            tagInRowTradeOffsetText.innerText = "%";
            break;

        case 'SMA':
        case 'EMA':
            tagInRowValue.value = 20;            
            tagInRowTradeOffsetText.innerText = "%";
            tagInRowTriggerSelect.hidden = false;
            changeTriggerSelect(tagInRowTriggerSelect)
            break;

        case 'BB':
            tagInRowValue.value = 20;
            tagInRowOutputSelect.hidden = false;           
            tagInRowTrigger.type = "hidden";
            tagInRowTradeOffsetText.innerText = "%";
            tagInRowTriggerTextLeft.innerText = "";
            tagInRowTriggerTextRight.innerText = "PRICE";
            break;     

        case 'Price':  ///After here no trigger offset needed 
            tagInRowValue.type = "hidden";   
            tagInRowValue.value = 0;
            TAGInterval.hidden = true;
            tagInRowTrigger.min = "0"; 
            tagInRowTrigger.step = "0.01";  
            tagInRowTriggerOffset.type = "hidden";
            tagInRowTriggerOffset.value = 0.0;
            break;

        case 'F&G':
            tagInRowValue.type = "hidden";   
            tagInRowValue.value = 0;
            TAGInterval.hidden = true;
            tagInRowTrigger.min = "0"; 
            tagInRowTrigger.step = "0.1";  
            tagInRowTriggerOffset.type = "hidden";
            tagInRowTriggerOffset.value = 0.0;
            break;

        case 'RSI':
            tagInRowValue.value = 14;
            tagInRowTrigger.min = "0"; 
            tagInRowTrigger.step = "0.01";  
            tagInRowTriggerOffset.type = "hidden";
            tagInRowTriggerOffset.value = 0.0;
            break;

        case 'ADX':
            tagInRowValue.value = 14;
            tagInRowTrigger.min = "0"; 
            tagInRowTrigger.step = "0.01";  
            tagInRowTriggerOffset.type = "hidden";
            tagInRowTriggerOffset.value = 0.0;
            break;

        case 'ROC':            
            tagInRowValue.value = 9;
            tagInRowTrigger.min = "-100"; 
            tagInRowTrigger.step = "0.01";  
            tagInRowTriggerOffset.type = "hidden";
            tagInRowTriggerOffset.value = 0.0;
            break;
    }
}
//Function when enable state is changed
function changeOnEnablechange(selectedElement){        
    const selectedValue = selectedElement.value;
    const selectedRow = selectedElement.closest("tr"); 
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
    const selectedRow = selectedElement.closest("tr"); 
    const tagInRowTrigger = selectedRow.querySelector('#Trigger'); //Get elemet imput of trigger  
 
     switch (selectedValue) {
        case 'Price':
            tagInRowTrigger.type = "hidden"; 
                break;
        default: 
            tagInRowTrigger.type = "number";
            tagInRowTrigger.min = "0"; 
            tagInRowTrigger.step = "1"; 
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
    cell2.innerHTML = ` <label  id="pVal1" for="Value"></label> <input type="number" min="0" step="1"  id="Value" name="Dynamic${side}Value" value = 20> 
                        <label  id="pVal2" for="Value2"></label> <input type="hidden"  min="0" step="1" id="Value2" name="Dynamic${side}Value2" value = 0>
                        <label  id="pVal3" for="Value3"></label> <input type="hidden"  min="0" step="1" id="Value3" name="Dynamic${side}Value3" value = 0>
                        <label  id="pVal4" for="Value4"></label> <input type="hidden"  min="0" step="1" id="Value4" name="Dynamic${side}Value4" value = 0>
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
                        <select name="Dynamic${side}TriggerSelect" id="TriggerSelect">
                            <option value="Price">Price</option>
                            <option value="SMA">SMA</option>
                            <option value="EMA">EMA</option>
                        </select>    
                        <input type="hidden" step="0.01" id="Trigger" name="Dynamic${side}Trigger" value = 0 > 
                        <span id="pRTrigger"></span>`;
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
