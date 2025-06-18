var categories = [
    {
        "name": "laptops",
        "columns": [
            {title: "CPU", field: "cpu", headerFilter: true},
            {title: "RAM", field: "ram", headerFilter: true},
            {title: "Storage", field: "storage", headerFilter: true},
            {title: "GPU", field: "gpu", headerFilter: true}
        ]
    },
    {
        "name": "monitors",
        "columns": [
            {title: "Resolution", field: "resolution", headerFilter: true},
            {title: "Size", field: "size", headerFilter: true},
            {title: "Refresh rate", field: "refresh_rate", headerFilter: true},
            {title: "Panel", field: "panel", headerFilter: true}
        ]
    }
];
var categoryNames = categories.map(category => category.name);

function loadInventory(categoryName) {
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

    var rowClickHandler = function(e, row){
        let productData = row.getData();

        let imageHTML = productData.images.map(
            imageUrl => `<img src="${imageUrl}" style="display: inline-block; max-with: 180px; max-height: 180px; border: 1px solid; border-radius: 2px; margin-right: 4px" />`
        ).join('')

        let popupHtml = `
            <div class="modal-gallery" style="overflow: auto; overflow: auto; white-space: nowrap;"
                onWheel="this.scrollLeft+=event.deltaY>0?100:-100"> <!-- https://stackoverflow.com/questions/18481308/set-mouse-wheel-to-horizontal-scroll-using-css -->
                ${imageHTML}
            </div>
        `;

        Swal.fire({
            title: `${productData.title} <span style="color: #777;" class="popup-title-price">(${productData.price}€)</span>`,
            html: popupHtml,
            width: 800,
            animation: false,
            showCloseButton: true,
            showCancelButton: false,
            showConfirmButton: false,
            footer: `<a href="${productData.url}" target="_blank" style="display: inline-block; padding: 10px 40px; text-decoration: none; border: 1px solid; text-align: center; border-radius: 4px;">Open</a>`
          });

        return null;
    };

    if (!categoryNames.includes(categoryName)) {
        categoryName = categoryNames[0];
    }
    var categoryColumns = categories.find(category => category.name == categoryName).columns;

    var banknoteInventoryURL = `inventory/${categoryName}/normalized.json`;

    var timestampTrustThreshold = moment(0) // failsafe value that doesn't affect sorting
    var initialScrapeDurationEstimate = moment.duration(30, 'minutes');

    // a copy from Tabulator's src since it's inaccessible here
    function localStorageTest() {
        const testKey = "_tabulator_test";

        try {
            window.localStorage.setItem(testKey,testKey);
            window.localStorage.removeItem(testKey);
            return true;
        } catch (e) {
            return false;
        }
    }

    const persistenceMode = localStorageTest() ? "local" : "cookie";

    /**
     * Treat the query param value as a list of form values, not JSON,
     * e.g., headerFilter[0]["field"]="cpu"
     *
     * @param string fieldName
     * @returns {any|null}
     */
    function getListObjectFieldFromUrl(fieldName) {
        if (!window.location.search) {
            return null;
        }

        const urlParams = new URLSearchParams(window.location.search);
        var result = {};
        var found = false;

        for (const [key, value] of urlParams.entries()) {
            const match = key.match(/^(\w+)\[(\d+)\]\[(\w+)\]$/);
            if (match && match[1] === fieldName) {
                if (!result[fieldName]) {
                    result[fieldName] = [{}];
                }
                result[fieldName][match[2]][match[3]] = value;
                found = true;
            } else if (key === fieldName) {
                return value;
            }
        }
        if (found) {
            return result[fieldName];
        }

        return null;
    }

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
                formatter:function(cell, formatterParams, onRendered){
                    //cell - the cell component
                    //formatterParams - parameters set for the column
                    //onRendered - function to call when the formatter has been rendered

                    var itemTimestamp = moment(cell.getValue())

                    if (itemTimestamp > timestampTrustThreshold) {
                        return itemTimestamp.format("L LTS");
                    } else {
                        return "" // do not display untrue values
                    }
                }},
            {title:"Title", field:"title", headerFilter: true},
            {title:"Price", field:"price",
                width: 70,
                hozAlign:"right",
                sorter:function(a, b, aRow, bRow, column, dir, sorterParams){
                    //a, b - the two values being compared
                    //aRow, bRow - the row components for the values being compared (useful if you need to access additional fields in the row data for the sort)
                    //column - the column component for the column being sorted
                    //dir - the direction of the sort ("asc" or "desc")
                    //sorterParams - sorterParams object from column definition array

                    /*
                        Not sure why i need to define a custom sorter,
                        but by default the values are compared as strings.
                    */
                    return a - b;
                },
                headerFilter: minMaxFilterEditor,
                headerFilterFunc: minMaxFilterFunction,
                headerFilterLiveFilter: false},
            ]
        .concat(categoryColumns)
        .concat([
            {title:"City", field:"city", headerFilter: true},
            {title:"Address", field:"local_address", headerFilter: true},
            {title:"URL", field:"url", headerFilter: true, formatter: "link"},
        ]),
        movableColumns: true,
        persistence: {
            sort: true,
            headerFilter: true,
            columns: true,
        },
        persistenceID: categoryName === "laptops" ? "example-table" : categoryName, // backwards compatibility
        persistenceReaderFunc: function (id, type) {
            // id - tables persistence id
            // type - type of data being persisted ("sort", "filter", "group", "page" or "columns")

            // Read from query parameter first, then from default storage
            // Ignore persistence ID, use the current category as context
            const typeFromUrl = getListObjectFieldFromUrl(type);
            if (typeFromUrl !== null) {
                return typeFromUrl;
            }

            return Tabulator.moduleBindings.persistence.readers[persistenceMode](id, type);
        },
        persistenceWriterFunc: function (id, type, data){
            // id - tables persistence id
            // type - type of data being persisted ("sort", "filter", "group", "page" or "columns")
            // data - array or object of data

            // If the type is in the query parameters, don't write to storage
            // Ignore persistence ID, use the current category as context
            const typeFromUrl = getListObjectFieldFromUrl(type);
            if (typeFromUrl !== null) {
                return;
            }

            Tabulator.moduleBindings.persistence.writers[persistenceMode](id, type, data);
        },
    });

    table.on("rowClick", rowClickHandler);

    document.getElementById("resetFiltersButton").onclick = function(){
        table.clearFilter(true);
    }
}

function toTitleCase(str) {
    return str.replace(/\w\S*/g, function(txt) {
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
    });
}

function switchMenu(categoryName) {
    var categoryMenu = document.getElementById("category-menu");
    var element = categoryMenu.children[categoryNames.indexOf(categoryName)];

    // construct the URL with category from selected category + current query parameters
    var url = new URL(window.location.origin + element.getAttribute("href"));
    var currentParams = new URLSearchParams(window.location.search);
    currentParams.set('category', categoryName);
    url.search = currentParams.toString();

    window.history.pushState({}, "", url);
    for (var i = 0; i < categoryMenu.children.length; i++) {
        categoryMenu.children[i].classList.remove("active");
    }
    element.classList.add("active");
    loadInventory(categoryName);
}

document.addEventListener('DOMContentLoaded', function() {
    var categoryMenu = document.getElementById("category-menu");
    categoryMenu.innerHTML = categories.map(category => `
        <a class="category-tab" href="?category=${category.name}" data-category="${category.name}">${toTitleCase(category.name)}</a>
    `).join(' ');

    categoryMenu.onclick = function(event) {
        if (event.target.classList.contains("category-tab")) {
            event.preventDefault();
            switchMenu(event.target.getAttribute("data-category"));
        }
    }

    var category = null;
    if (window.location.search) {
        category = (new URLSearchParams(window.location.search)).get('category');
    }
    if (category === null) {
        category = categoryNames[0];
    }
    switchMenu(category);
});
