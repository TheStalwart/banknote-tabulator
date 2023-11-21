Tabulator.extendModule("filter", "filters", {
    "===":function(headerValue, rowValue, rowData, filterParams){
        //headerValue - the value of the header filter element
        //rowValue - the value of the column in this row
        //rowData - the data for the row being filtered
        //filterParams - params object passed to the headerFilterFuncParams property

        return rowVal === headerValue ? true : false;
    }
});

function loadInventory() {
    var banknoteInventoryURL = "inventory/normalized.json"

    table = new Tabulator("#example-table", {
        index:"id",
        autoColumns: true,
        ajaxURL: banknoteInventoryURL,
        ajaxResponse:function(url, params, response){
            //url - the URL of the request
            //params - the parameters passed with the request
            //response - the JSON object returned in the body of the response.
            console.log(response)
            return response; //return the tableData property of a response json object
        },
    });

    table.on("dataLoadError", function(error){
        //error - the returned error object
        console.log(error)
    });

    table.on("tableBuilt", () => {
        console.log("tableBuilt")
    });

    // table.setData(banknoteInventoryURL)

    //Define variables for input elements
    var fieldEl = document.getElementById("filter-field");
    var typeEl = document.getElementById("filter-type");
    var valueEl = document.getElementById("filter-value");

    function updateFilter(){
        var filterVal = fieldEl.options[fieldEl.selectedIndex].value;
        var typeVal = typeEl.options[typeEl.selectedIndex].value;
      
        var filter = filterVal == "function" ? customFilter : filterVal;
      
        if(filterVal == "function" ){
          typeEl.disabled = true;
          valueEl.disabled = true;
        }else{
          typeEl.disabled = false;
          valueEl.disabled = false;
        }
      
        if(filterVal){
          table.setFilter(filter,typeVal, valueEl.value);
        }
    }
    
    //Update filters on value change
    document.getElementById("filter-field").addEventListener("change", updateFilter);
    document.getElementById("filter-type").addEventListener("change", updateFilter);
    document.getElementById("filter-value").addEventListener("keyup", updateFilter);

    //Clear filters on "Clear Filters" button click
    document.getElementById("filter-clear").addEventListener("click", function(){
        fieldEl.value = "";
        typeEl.value = "=";
        valueEl.value = "";

        table.clearFilter();
    });

    console.log("Finished loading inventory")
}
