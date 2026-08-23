export function setExpression(expression = "neutral", weight = 1) {
  this.currentExpression = expression;

  //reset
  for (const targetExpression in this.targetExpressionWeights) {
    this.targetExpressionWeights[targetExpression] = 0.0;
  }

  if(expression === "neutral") return;
  this.targetExpressionWeights[expression] = weight;
}
