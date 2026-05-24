//on change selection boxes
document.body.addEventListener('change', function(event) {
    const selectedElement = event.target; //Get actual element
    // Check if the event target is a <select> element
    if (selectedElement.tagName === 'SELECT') {
        const selectedValue = selectedElement.value;
        
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
