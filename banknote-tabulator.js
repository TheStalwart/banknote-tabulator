function loadInventory() {
    //custom max min header filter
    var minMaxFilterEditor = function(cell, onRendered, success, cancel, editorParams){

        var end;

        var container = document.createElement("span");

        //create and style inputs
        var start = document.createElement("input");
        start.setAttribute("type", "number");
        start.setAttribute("placeholder", "Min");
        start.style.padding = "4px";
        start.style.width = "100%";
        start.style.boxSizing = "border-box";

        start.value = cell.getValue();

        function buildValues(){
            success({
                start:start.value,
                end:end.value,
            });
        }

        function keypress(e){
            if(e.keyCode == 13){
                buildValues();
            }

            if(e.keyCode == 27){
                cancel();
            }
        }

        end = start.cloneNode();
        end.setAttribute("placeholder", "Max");

        start.addEventListener("change", buildValues);
        start.addEventListener("blur", buildValues);
        start.addEventListener("keydown", keypress);

        end.addEventListener("change", buildValues);
        end.addEventListener("blur", buildValues);
        end.addEventListener("keydown", keypress);


        container.appendChild(start);
        container.appendChild(document.createElement("br"));
        container.appendChild(end);

        return container;
    }

    //custom max min filter function
    function minMaxFilterFunction(headerValue, rowValue, rowData, filterParams){
        //headerValue - the value of the header filter element
        //rowValue - the value of the column in this row
        //rowData - the data for the row being filtered
        //filterParams - params object passed to the headerFilterFuncParams property

            if(rowValue){
                if(headerValue.start != ""){
                    if(headerValue.end != ""){
                        return rowValue >= headerValue.start && rowValue <= headerValue.end;
                    }else{
                        return rowValue >= headerValue.start;
                    }
                }else{
                    if(headerValue.end != ""){
                        return rowValue <= headerValue.end;
                    }
                }
            }

        return true; //must return a boolean, true if it passes the filter.
    }

    //create row popup contents
    var rowPopupFormatter = function(e, row, onRendered){
        var data = row.getData(),
        container = document.createElement("div")
        container.style = "max-height: 50%"
        contents = "<strong style='font-size:1.2em;'>" + data.price + " €: <a href='" + data.url + "'>" + data.title + "</a></strong><br/><ul style='padding:0;  margin-top:10px; margin-bottom:0;'>";
        data.images.forEach(image_url => {
            contents += "<li><img src='" + image_url + "'></li>";
        });
        contents += "</ul>";

        container.innerHTML = contents;

        return container;
    };

    var banknoteInventoryURL = "inventory/normalized.json"
    
    var timestampTrustThreshold = moment(0) // failsafe value that doesn't affect sorting
    var initialScrapeDurationEstimate = moment.duration(30, 'minutes');

    table = new Tabulator("#example-table", {
        index:"id",
        initialSort:[
            {column:"timestamp", dir:"desc"}, 
        ],
        ajaxURL: banknoteInventoryURL,
        ajaxResponse:function(url, params, response){
            //url - the URL of the request
            //params - the parameters passed with the request
            //response - the JSON object returned in the body of the response.
            document.getElementById('last_index_refresh').innerHTML = moment(response['index_file_modification_timestamp'], 'X').fromNow();
            moment.locale("lv");
            document.getElementById('last_index_refresh').title = moment(response['index_file_modification_timestamp'], 'X').format('llll');

            var oldestEntryTimestamp = moment(response['inventory'].sort((a, b) => {
                return moment(a["timestamp"]) - moment(b["timestamp"])
            })[0]["timestamp"])
            oldestEntryTimestamp.add(initialScrapeDurationEstimate)
            timestampTrustThreshold = oldestEntryTimestamp

            return response['inventory'];
        },
        columns: [
            {title:"SKU", field:"article", headerFilter: true, 
                sorter:"number",
                hozAlign:"right",
                headerSortStartingDir:"desc",
                headerTooltip: "Higher number == newer product"},
            {title:"ID", field:"id", headerFilter: true,
                hozAlign:"right",
                headerSortStartingDir:"desc",
                headerTooltip: "Internal ID for debugging"},
            {title:"Updated", field:"timestamp",
                sorter:function(a, b, aRow, bRow, column, dir, sorterParams){
                    //a, b - the two values being compared
                    //aRow, bRow - the row components for the values being compared (useful if you need to access additional fields in the row data for the sort)
                    //column - the column component for the column being sorted
                    //dir - the direction of the sort ("asc" or "desc")
                    //sorterParams - sorterParams object from column definition array

                    /*
                        Banknote doesn't publish timestamps of items,
                        so we use item json file modification times
                        for sorting by "item modification date".

                        Initial scrape took 20 minutes on my workstation,
                        so items older than first item timestamp + 30 minutes
                        should be sorted by article instead.
                    */
                    if (moment(a) < timestampTrustThreshold && moment(b) < timestampTrustThreshold) {
                        return aRow.getData().article - bRow.getData().article
                    } else {
                        return moment(a) - moment(b);
                    }
                },
                headerTooltip: "Sort by date to see recently discounted items",
                headerSortStartingDir:"desc",
                formatter:"datetime",
                formatterParams:{
                    inputFormat:"iso",
                }},
            {title:"Title", field:"title", headerFilter: true},
            {title:"Price", field:"price", 
                width: 70,
                hozAlign:"right",
                headerFilter: minMaxFilterEditor, 
                headerFilterFunc: minMaxFilterFunction, 
                headerFilterLiveFilter: false},
            {title:"CPU", field:"cpu", headerFilter: true},
            {title:"RAM", field:"ram", headerFilter: true},
            {title:"Storage", field:"storage", headerFilter: true},
            {title:"GPU", field:"gpu", headerFilter: true},
            {title:"City", field:"city", headerFilter: true},
            {title:"Address", field:"local_address", headerFilter: true},
            {title:"URL", field:"url", headerFilter: true, formatter: "link"},
        ],
        movableColumns: true,
        rowClickPopup:rowPopupFormatter, //add click popup to row
    });
}
