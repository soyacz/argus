## Components

### Single Responsibility
Each component should do one thing well.

### Reusability
Design components to work across different contexts with configurable props.

### Composability
Build complex UIs by combining smaller components rather than creating monoliths.

### Clear Interface
Define explicit, documented props with sensible defaults.

### Encapsulation
Keep implementation details private; expose only what's necessary.

### Consistent Naming
Use descriptive names that indicate purpose and follow team conventions.

### Local State
Keep state as close to where it's used as possible; lift only when needed.

### Minimal Props
If a component needs many props, consider composition or splitting it.

### Documentation
Document usage, props, and examples to help team adoption.

### Svelte 5 Runes
Use rune APIs for all reactivity: `$props()` for props (destructured), `$state()` for local state, `$derived()` for computed values, `run()` for effects. Do NOT use legacy `export let` or `$:` reactivity. Project is 99% migrated.

Preferred:
```svelte
let { data = $bindable() } = $props();
let editing = $state(false);
const computed = $derived(someExpression);
```

Avoid:
```svelte
export let data;
$: computed = someExpression;
```

### PascalCase Component Naming
All .svelte component files use PascalCase (e.g., `AdminPanel.svelte`, `ResultTable.svelte`). Components organized in PascalCase directories by feature area.

### No Direct DOM Querying
Use Svelte bindings (`bind:this`) or actions (`use:...`) instead of global selectors. Never call `querySelector` or `querySelectorAll` inside components.

### Composition Over Imperative DOM
Prefer component composition, snippets, and `@const`/`@render` blocks over imperative DOM updates. Use `await tick()` when waiting for DOM after state changes.

### Function Expression Style
Use `const fn = function(...)` for function declarations in Svelte/JS files:
```js
const handleClick = function (event) { ... };
```
