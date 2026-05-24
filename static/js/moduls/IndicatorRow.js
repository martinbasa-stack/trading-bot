export class IndicatorRow {
    constructor(tableBody, side) {
        this.side = side;
        this.row = this._createRow(tableBody, side);
        this._cacheElements();
        this._attachEvents();
    }

    _createRow(tableBody, side) {
        const row = tableBody.insertRow();

        row.innerHTML = `
        <td>
            <select id="Type" name="Dynamic${side}Type">
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
            </select>
        </td>
        <td>
            <label  id="pVal1" for="Value"></label> <input type="number" min="0" step="1"  id="Value" name="Dynamic${side}Value" value = 20> 
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
                <option value="1w">1w</option>
                <option value="1M">1M</option>
            </select>
        </td>
        <td>
            <input type="number" min="0" step="1" id="Weight" name="Dynamic${side}Weight" value = 0 >
        </td>
        <td>
            <input type="number" min="-90" max="90" step="0.01"  id="TradeOffset" name="Dynamic${side}BlockTradeOffset" value = 0>
            <span  id="pTradeOffset" >%</span>
        </td>
        <td>
            <select hidden name="Dynamic${side}OutputSelect" id="OutputSelect">
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
            <span id="pRTrigger"></span>
        </td>    
        <td>
            <select name="Dynamic${side}Enable" id="Enable">
                <option value="1">ON</option>
                <option value="0" selected>OFF</option>
            </select>
            <input class="disabledLook" type="number" min="0" step="0.1"  id="Factor" name="Dynamic${side}Factor" value = 0 > x Δ
        </td>
        <td>
            <input class="disabledLook" type="number" min="0" step="0.1"  id="Max" name="Dynamic${side}Max" value = 100.0 > %
        </td>
        <td>
            <button type="button"  class="remove-btn" >REMOVE</button>
        </td>
        `;

        return row;
    }

    _cacheElements() {
        const q = id => this.row.querySelector(id);

        this.el = {
            type: q('#Type'),
            comparator: q('#Comparator'),
            value1: q('#Value'),
            value2: q('#Value2'),
            value3: q('#Value3'),
            value4: q('#Value4'),
            weight: q('#Weight'),
            interval: q('#Interval'),
            triggerOffset: q('#TradeOffset'),
            pLTrigger: q('#pLTrigger'),
            trigger: q('#Trigger'),
            pRTrigger: q('#pRTrigger'),
            triggerSelect: q('#TriggerSelect'),
            pTriggerOffset: q('#pTradeOffset'),
            outputSelect: q('#OutputSelect'),
            enable: q('#Enable'),
            factor: q('#Factor'),
            max: q('#Max'),
            removeBtn: this.row.querySelector('.remove-btn')
        };
    }

    _attachEvents() {
        this.el.type.addEventListener('change', () => this.onTypeChange());
        this.el.triggerSelect.addEventListener('change', () => this.onTriggerSelect());
        this.el.enable.addEventListener('change', () => this.onEnableChange());
        this.el.removeBtn.addEventListener('click', () => this.row.remove());
    }

    /* === ORIGINAL FUNCTIONS TURNED INTO CLASS METHODS === */

    onTypeChange() {
        const selected = this.el.type.value;

        // reset default state
        this.el.triggerSelect.hidden = true;
        this.el.outputSelect.hidden = true;

        this.el.value1.type = "number";
        this.el.trigger.type = "number";
        this.el.triggerOffset.type = "number";
        
        this.el.interval.hidden = false;

        this.el.pTriggerOffset.innerText = "";
        this.el.pRTrigger.innerText = "";
        this.el.pLTrigger.innerText = selected;

        switch (selected) {
            case "AvrageCost":
            case "AvrageEntry":
            case "AvrageExit":
                this.el.value1.type = "hidden";
                this.el.value1.value = 0;
                this.el.trigger.type = "hidden";
                this.el.interval.hidden = true;
                this.el.pRTrigger.innerText = "PRICE";
                this.el.pTriggerOffset.innerText = "%";
                break;

            case "SMA":
            case "EMA":
                this.el.value1.value = 20;
                this.el.pTriggerOffset.innerText = "%";
                this.el.triggerSelect.hidden = false;
                this.onTriggerSelect();  // apply inner type change
                break;

            case "BB":
                this.el.value1.value = 20;
                this.el.outputSelect.hidden = false;
                this.el.trigger.type = "hidden";
                this.el.pTriggerOffset.innerText = "%";
                this.el.pLTrigger.innerText = "";
                this.el.pRTrigger.innerText = "PRICE";
                break;

            case "Price":
            case "F&G":
                this.el.value1.type = "hidden";
                this.el.value1.value = 0;
                this.el.interval.hidden = true;
                this.el.trigger.min = "0";
                this.el.trigger.step = "0.1";
                this.el.triggerOffset.type = "hidden";
                this.el.triggerOffset.value = 0;
                break;

            case "RSI":
            case "ADX":
                this.el.value1.value = 14;
                this.el.trigger.min = "0";
                this.el.trigger.step = "0.01";
                this.el.triggerOffset.type = "hidden";
                this.el.triggerOffset.value = 0;
                break;

            case "ROC":
                this.el.value1.value = 9;
                this.el.trigger.min = "-100";
                this.el.trigger.step = "0.01";
                this.el.triggerOffset.type = "hidden";
                this.el.triggerOffset.value = 0;
                break;
        }
    }

    onEnableChange() {
        const isEnabled = this.el.enable.value === "1";
        this.el.factor.classList.toggle("disabledLook", !isEnabled);
        this.el.max.classList.toggle("disabledLook", !isEnabled);
    }

    onTriggerSelect() {
        const sel = this.el.triggerSelect.value;
        if (sel === "Price") {
            this.el.trigger.type = "hidden";
        } else {
            this.el.trigger.type = "number";
            this.el.trigger.min = "0";
            this.el.trigger.step = "1";
        }
    }

    // ---------------------------
    // Load data from Flask
    // ---------------------------
    load(data) {
        this.el.type.value = data.Type;
        this.el.comparator.value = data.Comparator;
        this.el.value1.value = data.Value;
        this.el.value2.value = data.Value2;
        this.el.value3.value = data.Value3;
        this.el.value4.value = data.Value4;
        this.el.weight.value = data.Weight;
        this.el.interval.value = data.Interval;
        this.el.triggerOffset.value = data.BlockTradeOffset;
        this.el.trigger.value = data.Trigger;
        this.el.triggerSelect.value = data.TriggerSelect;
        this.el.outputSelect.value = data.OutputSelect;
        this.el.enable.value = data.Enable ? 1 : 0;
        this.el.factor.value = data.Factor;
        this.el.max.value = data.Max;

        // auto re-run UI logic
        this.onTypeChange();
        this.onEnableChange();
    }

    destroy() {
        this.row.remove();
    }
}

