const fs = require("node:fs");
const vm = require("node:vm");

const tabulatorFilters = {
    "=": (filterVal, rowVal) => rowVal == filterVal,
    "<": (filterVal, rowVal) => rowVal < filterVal,
    "<=": (filterVal, rowVal) => rowVal <= filterVal,
    ">": (filterVal, rowVal) => rowVal > filterVal,
    ">=": (filterVal, rowVal) => rowVal >= filterVal,
    like: (filterVal, rowVal) => {
        if (filterVal === null || typeof filterVal === "undefined") {
            return rowVal === filterVal;
        }

        if (typeof rowVal !== "undefined" && rowVal !== null) {
            return String(rowVal).toLowerCase().indexOf(filterVal.toLowerCase()) > -1;
        }

        return false;
    },
};

const context = {
    console: console,
    document: {addEventListener: () => {}},
    window: {},
    Tabulator: {
        moduleBindings: {
            filter: {filters: tabulatorFilters},
        },
    },
};
context.globalThis = context;

vm.createContext(context);
vm.runInContext(fs.readFileSync("banknote-tabulator.js", "utf8"), context);

const assertEqual = (name, actual, expected) => {
    if (actual !== expected) {
        throw new Error(name + ": expected " + expected + ", got " + actual);
    }
};


// reset caches
context.numericFilterExpressionCache = {};
context.numericRowValueCache = {};

const capacityParams = {parseCapacity: true};
const storageParams = {parseCapacity: true};
const genericParams = {};

[
    ["RAM parses GB", context.parseNumericRowValue("8 GB", capacityParams), 8],
    ["RAM parses compact GB", context.parseNumericRowValue("16GB", capacityParams), 16],
    ["RAM ignores DDR prefix", context.parseNumericRowValue("DDR4 16GB", capacityParams), 16],
    ["RAM ignores multiplier prefix", context.parseNumericRowValue("2x8GB DDR4", capacityParams), 8],
    ["RAM converts MB", context.parseNumericRowValue("8192 MB", capacityParams), 8],
    ["RAM parses Cyrillic GB", context.parseNumericRowValue("16 ГБ Память", capacityParams), 16],
    ["Storage parses TB", context.parseNumericRowValue("1 TB SSD", storageParams), 1024],
    ["Storage parses T shorthand", context.parseNumericRowValue("3T SSD", storageParams), 3072],
    ["Storage parses decimal TB", context.parseNumericRowValue("1.5 TB SSD (1 TB NVMe + 500 GB NVMe)", storageParams), 1536],
    ["Storage parses TBGB typo as TB", context.parseNumericRowValue("1TBGB SSD", storageParams), 1024],
    ["Storage parses G shorthand", context.parseNumericRowValue("128G SSD", storageParams), 128],
    ["Storage parses Cyrillic TB/GB", context.parseNumericRowValue("HDD 1 TБ/ SSD 256 ГБ", storageParams), 1024],
    ["Storage ignores Gen4 before TB", context.parseNumericRowValue("NVMe PCIe Gen4 SSD 1TB", storageParams), 1024],
    ["Storage ignores model numbers", context.parseNumericRowValue("Samsung SSD 970 EVO Plus 250GB", storageParams), 250],
    ["Storage picks largest capacity", context.parseNumericRowValue("256 GB SSD, 1 TB HDD", storageParams), 1024],
    ["Storage does not sum mirrored notation", context.parseNumericRowValue("2x 512GB SSD", storageParams), 512],
    ["Storage parses bare number before SSD", context.parseNumericRowValue("512 SSD", storageParams), 512],
    ["Storage parses bare number after SSD", context.parseNumericRowValue("SSD 256", storageParams), 256],
    ["Storage rejects typo unit HB", context.parseNumericRowValue("512HB SSD", storageParams), null],
    ["Storage rejects model without capacity", context.parseNumericRowValue("Optiarc DVD RW AD-7280S", storageParams), null],
    ["Generic size still parses first number", context.parseNumericRowValue("27\"", genericParams), 27],
    ["Generic refresh still parses first number", context.parseNumericRowValue("144 Hz", genericParams), 144],
].forEach((testCase) => {
    assertEqual(testCase[0], testCase[1], testCase[2]);
});

assertEqual(">8 excludes 8GB", context.numericTextFilterFunc(">8", "8 GB", null, capacityParams), false);
assertEqual(">=8 includes 8GB", context.numericTextFilterFunc(">=8", "8 GB", null, capacityParams), true);
assertEqual(">1000 includes 1TB", context.numericTextFilterFunc(">1000", "1 TB SSD", null, storageParams), true);
assertEqual("plain 8 uses text fallback", context.numericTextFilterFunc("8", "18 GB", null, capacityParams), true);
assertEqual("unit query is not numeric syntax", context.numericTextFilterFunc(">1tb", "1536 GB", null, storageParams), false);
assertEqual("decimal query is not numeric syntax", context.numericTextFilterFunc(">1.5", "2 GB", null, capacityParams), false);

console.log("ok");
