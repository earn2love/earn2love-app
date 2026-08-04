"use strict";

const CALL_COSTS = Object.freeze({
  audio: Object.freeze({
    callerPerMin: 10,
    receiverPerMin: 2,
  }),
  video: Object.freeze({
    callerPerMin: 25,
    receiverPerMin: 5,
  }),
});

module.exports = {
  CALL_COSTS,
};
