
async function pageFunction(context) {
    const $ = context.jQuery;
    const containers = $('[data-lyrics-container="true"]');

    const details = [];

    containers.each(function(index, element) {
        const container = $(element);

        details.push({
            index: index,
            tag: element.tagName,
            className: container.attr('class') || '',
            childCount: container.children().length,
            textStart: container.text().slice(0, 150),
            htmlStart: container.html().slice(0, 500)
        });
    });

    return {
        url: context.request.url,
        container_count: containers.length,
        container_details: details
    };
}
