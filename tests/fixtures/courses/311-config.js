/**
 *
 * Configure your course website here:
 *
 */

const courseNumber = "CSE 311";
const courseTitle = "Foundations of Computing I";
const quarter = "26au";

// Set this to true to display an archive banner on the site. This should be done once the site will no longer be maintained
const isArchived = false;

const cssFiles = [
    { fileName: 'bootstrap.min.css' },
    { fileName: 'main.css' },
    { fileName: 'calendar.css' },
    { fileName: 'https://fonts.googleapis.com/css?family=Source+Sans+Pro:400,400italic,600', absolute: true }
];

const jsFiles = [
    { fileName: 'bootstrap.min.js' }
];

// HTML files to be inserted, and the ID of the element they should be added within
const htmlFiles = [
    { fileName: 'top-nav.html', elementId: '#top-navbar' },
    { fileName: 'footer.html', elementId: '#footer'},
];


/**
 *
 * End of configuration - all of the below is nuts and bolts!
 *
 */
const baseURL = getBaseURL();
loadPage();

// Get the URL of the current directory, so we don't run into relative URL issues
function getBaseURL() {
    const currentScriptDir = document.currentScript;
    const baseURL = new URL('../..', currentScriptDir.src).href;
    return baseURL;
}

// Import CSS, Javascript, and HTML files
async function loadPage() {
    // Start off by hiding the page so we don't get a flash of unstyled content
    document.documentElement.style.visibility = 'hidden';

    for (const cssFile of cssFiles) {
        await loadCSSFile(cssFile);
    }

    for (const jsFile of jsFiles) {
        await loadJavacriptFile(jsFile);
    }

    renderHTML();
}

function loadCSSFile(cssFile) {
    return new Promise((resolve, reject) => {
        const css = document.createElement('link');

        if (cssFile.absolute) {
            css.href = cssFile.fileName;
        } else {
            css.href = baseURL + 'site/css/' + cssFile.fileName;
        }

        css.rel = 'stylesheet';
        css.onload = resolve;
        css.onerror = reject;
        document.head.appendChild(css);
    });
}

function loadJavacriptFile(jsFile) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');

        if (script.absolute) {
            script.src = jsFile.fileName;
        } else {
            script.src = baseURL + 'site/js/' + jsFile.fileName;
        }

        script.defer = true;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

async function renderHTML() {
    // Display the archive banner if this site is no longer udpated
    if (isArchived) {
        htmlFiles.push({ fileName: '/archive-banner.html', elementId: '#archive-banner' });
    }

    // Load all of the page's HTML files, such as header and footer
    for (const file of htmlFiles) {
        await insertHTMLFile(file);
    }

    // Once all of our HTML files have been loaded, then we populate our template variables, and un-hide the page
    setMainHeader();
    setPageTitle();
    setQuarter();
    setActiveNavItem();
    setWordmarkImagePath();
    showPage();
}

// Insert HTML content into a specific element on the page
async function insertHTMLFile(file) {
    const element = document.querySelector(file.elementId);

    if (!element) {
        return;
    }

    const res = await fetch(new URL('site/' + file.fileName, baseURL));
    element.innerHTML = await res.text();
}

function setMainHeader() {
    // Display the course number and title
    document.querySelector('.navbar-brand h1').textContent = courseNumber + ': ' + courseTitle;

    // Link the course title to the overview page for this course
    let courseOverviewPageURL = new URL('..', baseURL).href;
    document.querySelector('a.navbar-brand').setAttribute('href', courseOverviewPageURL);
}

// If present, append the per-page subtitle to the document title
function setPageTitle() {
    let title = courseNumber;
    let subtitle = document.querySelector('h2.subtitle');

    if (subtitle && subtitle.length === 1) {
        title = title + ' - ' + subtitle.textContent;
    }

    document.title = title;
}

function setQuarter() {
    document.querySelector('#course-quarter').append(quarter);
}

function setWordmarkImagePath() {
    let wordmarkImage = document.querySelector('.cse-wordmark img');
    let wordmarkPath = baseURL + '/site/img/CSEWordmark_sm.png';
    wordmarkImage.setAttribute('src', wordmarkPath);
}

// Set the "active" class on the currently selected item.
// This toggles the menu item's background color.
// It is looking for a part of the URL that matches a non-empty href string
// of a menu item. If a match is found, that item is considered active.
function setActiveNavItem() {
    var thishref = window.location.href;
    var tokens = thishref.split("/");

    document.querySelectorAll(".navbar-nav a[href]").forEach((navItem) => {
        navItem.classList.remove('active');
        navItem.removeAttribute('aria-current');

        var href = navItem.getAttribute('href');

        if ((href !== '') && tokens.includes(href)) {
            navItem.classList += ' active';
            navItem.setAttribute('aria-current', 'page');
        }

        fixNavItemHref(navItem);
    });
}

// Prepend the base URL to each href unless it's an absolute URL
function fixNavItemHref(navItem) {
    let href = navItem.getAttribute('href');

    if ((href.startsWith('http') === true) || (href.startsWith('/') === true)) {
        return;
    }

    let basePage  = new URL('.', baseURL).href;
    navItem.setAttribute("href", basePage + href);
}

// The page html is hidden at the start to avoid a flash of unstyled content before the page is fully loaded.
// Once this function is called, then the whole page will be visible
function showPage() {
    document.documentElement.style.visibility = 'visible';
}
