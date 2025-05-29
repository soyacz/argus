# Description
Instructions for investigating test failures related to frontend user interface components, including element not found errors, timing issues, browser compatibility problems, and JavaScript execution failures.

# Instructions
When investigating UI component test failures:

1. Check if the target UI element exists in the DOM
2. Verify element selectors (CSS, XPath) are correct and unique
3. Add explicit waits for dynamic content loading
4. Check browser console for JavaScript errors or warnings
5. Verify browser compatibility with the tested application
6. Examine network requests for failed resource loading
7. Check for pop-ups or modal dialogs blocking interactions
8. Verify viewport size and responsive design considerations
9. Look for timing issues with AJAX requests or animations
10. Check for iframe context switching requirements
11. Verify file upload/download functionality if applicable
12. Examine screenshot evidence for visual regression issues
13. Check for browser-specific CSS or JavaScript issues
