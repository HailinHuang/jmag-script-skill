# Case numbering

The public library accepts strict 1-based integer case numbers. Validate against `DesignTable.NumCases()` and translate once to the zero-based JMAG API index. Reject booleans, duplicates, empty subsets, and out-of-range values before starting a run or write.
