function create_bar_chart(canvasId, labels, datasets, chartTitle) {
    new Chart(document.getElementById(canvasId), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: chartTitle,
                    font: {size: 18}
                },
                legend: {position: 'top'},
                datalabels: {
                    anchor: 'end',
                    align: 'end',
                    color: '#000',
                    rotation: labels.length > 7 ? -90 : 0,
                    formatter: value => value
                }
            },
            scales: {
                y: {beginAtZero: true}
            }
        },
        plugins: [ChartDataLabels]
    });
}

function create_utilities_cards(containerId, dataList) {
    const container = document.getElementById(containerId);

    const row = document.createElement('div');
    row.className = 'row mt-3';

    const itemCount = dataList.length;
    // Bootstrap grid has 12 columns, so divide 12 by number of items, min 1, max 12
    const colSize = Math.min(12, Math.max(1, Math.floor(12 / itemCount)));

    dataList.forEach(item => {
        const col = document.createElement('div');
        col.className = `col-12 col-md-${colSize} mb-3`;

        col.innerHTML = `
        <div class='card h-100 shadow-sm'>
            <div class='card-body text-center d-flex flex-column justify-content-center'>
                <h6 class='card-title text-muted mb-2'>${item.title}</h6>
                <h1 class='card-text font-weight-bold mb-0'>${item.value}</h1>
            </div>
        </div>
    `;

        row.appendChild(col);
    });

    container.appendChild(row);
}

function create_table(containerId, title, dataset) {
    const container = document.getElementById(containerId);

    // Create title
    if (title) {
        const titleElement = document.createElement("h6");
        titleElement.className = "card-title text-muted mb-2 text-center";
        titleElement.textContent = title;
        container.appendChild(titleElement);
    }

    if (!Array.isArray(dataset) || dataset.length === 0) {
        const emptyMessage = document.createElement("p");
        emptyMessage.textContent = "No data available";
        container.appendChild(emptyMessage);
        return;
    }

    // Create table
    const table = document.createElement("table");
    table.className = "table table-sm";

    // Get columns dynamically
    const columns = Object.keys(dataset[0]);

    // Create thead
    const thead = document.createElement("thead");
    thead.className = "thead-dark";

    const headerRow = document.createElement("tr");

    columns.forEach(col => {
        const th = document.createElement("th");
        th.textContent = col;
        headerRow.appendChild(th);
    });

    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Create tbody
    const tbody = document.createElement("tbody");

    dataset.forEach(rowData => {
        const row = document.createElement("tr");

        columns.forEach(col => {
            const td = document.createElement("td");
            td.textContent = rowData[col] ?? "";
            row.appendChild(td);
        });

        tbody.appendChild(row);
    });

    table.appendChild(tbody);

    container.appendChild(table);
}

function create_line_graph(xLabels, yData, element, borderColor, label) {

    const data = {
        labels: xLabels,
        datasets: [{
            label: label,
            data: yData,
            borderColor: borderColor,
            tension: 0.2,
            fill: true,
            pointRadius: 3
        }]
    };

    new Chart(document.getElementById(element), {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            plugins: {
                legend: {position: 'top'},
                tooltip: {mode: 'index', intersect: false}
            },
            interaction: {mode: 'nearest', intersect: false},
            scales: {
                x: {
                    title: {display: true, text: 'Date'},
                    ticks: {maxRotation: 90, minRotation: 45}
                },
                y: {
                    title: {display: true, text: 'm³'},
                    beginAtZero: false
                }
            }
        }
    });
}