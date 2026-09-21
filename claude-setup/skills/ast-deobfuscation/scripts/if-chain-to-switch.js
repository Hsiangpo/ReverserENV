const { clone, generator, parseArgs, parseFile, reparse, saveAst, t, traverse } = require("./shared");

function normalizeCode(node) {
  return generator(node, {
    compact: true,
    comments: false,
    jsescOption: { minimal: true }
  }).code;
}

function getCaseInfo(testNode) {
  if (!t.isBinaryExpression(testNode) || testNode.operator !== "===") {
    return null;
  }

  const leftLiteral = t.isLiteral(testNode.left);
  const rightLiteral = t.isLiteral(testNode.right);
  if (leftLiteral === rightLiteral) {
    return null;
  }

  if (leftLiteral) {
    return {
      discriminant: testNode.right,
      caseValue: testNode.left
    };
  }

  return {
    discriminant: testNode.left,
    caseValue: testNode.right
  };
}

function toCaseStatements(node) {
  if (!node) {
    return [];
  }
  if (t.isBlockStatement(node)) {
    return node.body.map((stmt) => clone(stmt));
  }
  return [clone(node)];
}

function unwrapAlternate(path) {
  if (!path.node) {
    return { kind: "empty", path: null, node: null };
  }
  if (path.isIfStatement()) {
    return { kind: "if", path, node: path.node };
  }
  if (path.isBlockStatement()) {
    const body = path.get("body");
    if (body.length === 1 && body[0].isIfStatement()) {
      return { kind: "if", path: body[0], node: body[0].node };
    }
    return { kind: "default", path, node: path.node };
  }
  return { kind: "default", path, node: path.node };
}

function isTerminalStatement(node) {
  return t.isReturnStatement(node) || t.isThrowStatement(node) || t.isBreakStatement(node) || t.isContinueStatement(node);
}

function hasSafeDiscriminant(node, path) {
  // Repeated property reads/calls can have observable effects. Even an
  // identifier can hit a global accessor or a with-object instead of a local.
  if (!t.isIdentifier(node) || path.findParent(parent => parent.isWithStatement())) {
    return false;
  }
  const binding = path.scope.getBinding(node.name);
  if (!binding) {
    return false;
  }
  return !binding.scope.path.isProgram() || binding.kind === "let" || binding.kind === "const";
}

function canFlattenBranch(branchPath) {
  if (branchPath.isBreakStatement() || branchPath.isContinueStatement()) {
    return false;
  }
  if (branchPath.isBlockStatement() && branchPath.node.body.some(statement =>
    (t.isVariableDeclaration(statement) && statement.kind !== "var") ||
    t.isClassDeclaration(statement) || t.isFunctionDeclaration(statement)
  )) {
    return false;
  }
  let hasTransfer = false;
  branchPath.traverse({
    Function(path) {
      path.skip();
    },
    "BreakStatement|ContinueStatement"(path) {
      hasTransfer = true;
      path.stop();
    }
  });
  return !hasTransfer;
}

function collectIfChain(path) {
  if (path.parentPath.isIfStatement() && path.key === "alternate") {
    return null;
  }

  let currentPath = path;
  let discriminantCode = null;
  let discriminantNode = null;
  const cases = [];
  let defaultStatements = null;

  while (currentPath && currentPath.isIfStatement()) {
    const info = getCaseInfo(currentPath.node.test);
    if (!info || !hasSafeDiscriminant(info.discriminant, currentPath) ||
        !canFlattenBranch(currentPath.get("consequent"))) {
      return null;
    }

    const currentCode = normalizeCode(info.discriminant);
    if (discriminantCode === null) {
      discriminantCode = currentCode;
      discriminantNode = clone(info.discriminant);
    } else if (currentCode !== discriminantCode) {
      return null;
    }

    cases.push({
      test: clone(info.caseValue),
      statements: toCaseStatements(currentPath.node.consequent)
    });

    const alternate = unwrapAlternate(currentPath.get("alternate"));
    if (alternate.kind === "empty") {
      break;
    }
    if (alternate.kind === "if") {
      currentPath = alternate.path;
      continue;
    }
    if (!canFlattenBranch(alternate.path)) {
      return null;
    }
    defaultStatements = toCaseStatements(alternate.node);
    break;
  }

  if (cases.length < 2) {
    return null;
  }

  return {
    discriminant: discriminantNode,
    cases,
    defaultStatements
  };
}

function buildSwitchStatementFromChain(chain) {
  const switchCases = chain.cases.map((entry) => {
    const statements = entry.statements.slice();
    if (statements.length === 0 || !isTerminalStatement(statements[statements.length - 1])) {
      statements.push(t.breakStatement());
    }
    return t.switchCase(entry.test, statements);
  });

  if (chain.defaultStatements) {
    switchCases.push(t.switchCase(null, chain.defaultStatements));
  }

  return t.switchStatement(chain.discriminant, switchCases);
}

function rewrite(ast) {
  let changed = false;

  traverse(ast, {
    IfStatement(path) {
      const chain = collectIfChain(path);
      if (!chain) {
        return;
      }

      path.replaceWith(buildSwitchStatementFromChain(chain));
      changed = true;
    }
  });

  return { ast, changed };
}

const { inputPath, outputPath } = parseArgs();
let ast = parseFile(inputPath);
let changed = false;
do {
  ({ ast, changed } = rewrite(ast));
  if (changed) {
    ast = reparse(ast);
  }
} while (changed);
saveAst(ast, outputPath);
